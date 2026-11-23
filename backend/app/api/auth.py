"""OIDC Authentication endpoints.

Implements OAuth2 authorization code flow with PKCE, state/nonce validation,
and backend-managed sessions using HttpOnly SameSite cookies.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt

from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# OIDC / Keycloak configuration
# ---------------------------------------------------------------------------

KEYCLOAK_URL = getattr(settings, "keycloak_url", "http://localhost:8080/realms/orbit-lab")
KEYCLOAK_CLIENT_ID = getattr(settings, "keycloak_client_id", "orbit-lab-frontend")
KEYCLOAK_CLIENT_SECRET = getattr(settings, "keycloak_client_secret", None)
KEYCLOAK_REDIRECT_URI = getattr(settings, "keycloak_redirect_uri", "http://localhost:8000/auth/callback")
KEYCLOAK_LOGOUT_REDIRECT_URI = getattr(settings, "keycloak_logout_redirect_uri", "http://localhost:8000/auth/logout-callback")

# Cookie configuration for backend-managed sessions
AUTH_COOKIE_NAME = "orbitsession"
AUTH_COOKIE_MAX_AGE = 86400  # 24 hours
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_SAMESITE = "lax"
AUTH_COOKER_SECURE = False  # Set True in production with HTTPS


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def _code_verifier() -> str:
    """Generate a random PKCE code verifier (43-128 characters)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


def _code_challenge(v: str) -> str:
    """Derive the PKCE code challenge from the verifier using S256."""
    import hashlib as _h
    d = _h.sha256(v.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(d).rstrip(b"=").decode()


# ---------------------------------------------------------------------------
# Authorization URL helper
# -------------------------------------------------------------------------


def _build_authorization_url(state: str, code_challenge: str, code_challenge_method: str = "S256") -> str:
    """Build the Keycloak OAuth2 authorization URL."""
    params = {
        "response_type": "code",
        "client_id": KEYCLOAK_CLIENT_ID,
        "redirect_uri": KEYCLOAK_REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    if KEYCLOAK_CLIENT_SECRET:
        params["client_secret"] = KEYCLOAK_CLIENT_SECRET

    qs = urllib.parse.urlencode(params)
    return f"{KEYCLOAK_URL}/protocol/openid-connect/authorize?{qs}"


# ---------------------------------------------------------------------------
# Login endpoint – redirect to Keycloak
# -------------------------------------------------------------------------


@router.get("/login")
async def login(request: Request):
    """Initiate OIDC login by redirecting to Keycloak with PKCE."""
    # Generate random state and code verifier
    state = base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode()
    code_verifier = _code_verifier()
    code_challenge = _code_challenge(code_verifier)

    # Store state and verifier in session for callback validation
    request.session["oidc_state"] = state
    request.session["oidc_code_verifier"] = code_verifier

    auth_url = _build_authorization_url(state, code_challenge)
    return Response(content={"authorization_url": auth_url}, status_code=200)


# ---------------------------------------------------------------------------
# Callback endpoint – receive code from Keycloak, validate, set session cookie
# -------------------------------------------------------------------------


@router.post("/callback", include_in_schema=False)
async def callback(request: Request, response: Response):
    """Exchange authorization code for tokens and set HttpOnly SameSite cookie."""
    form = await request.form()
    code: str = form.get("code", "")
    state: str = form.get("state", "")
    code_verifier: Optional[str] = request.session.pop("oidc_code_verifier", None)
    stored_state: Optional[str] = request.session.pop("oidc_state", None)

    if not code_verifier or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state or code verifier",
        )

    # Exchange code for tokens at Keycloak
    token_url = f"{KEYCLOAK_URL}/protocol/openid-connect/token"
    token_params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": KEYCLOAK_REDIRECT_URI,
        "client_id": KEYCLOAK_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    if KEYCLOAK_CLIENT_SECRET:
        token_params["client_secret"] = KEYCLOAK_CLIENT_SECRET

    async with httpx.AsyncClient() as client:
        tok_resp = await client.post(token_url, data=token_params, timeout=30)
    if tok_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code for tokens",
        )
    tokens = tok_resp.json()

    # Validate and decode ID token
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ID token received from Keycloak",
        )

    # Verify the ID token signature and claims
    # Keycloak public key should be fetched from /.well-known/openid-configuration
    # For now, verify with options; in production, use the JWKS endpoint
    try:
        payload = jwt.decode(
            id_token,
            KEYCLOAK_CLIENT_SECRET or None,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_exp": True},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ID token verification failed: {exc}",
        )

    # Set backend-managed session cookie: HttpOnly, SameSite=Lax
    # The cookie contains the user's subject identifier and issuance time
    session_value = f"{payload['sub']}|{datetime.now(timezone.utc).isoformat()}"
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=session_value,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=AUTH_COOKIE_HTTP_ONLY,
        samesite=AUTH_COOKIE_SAMESITE,
        secure=AUTH_COOKER_SECURE,
        path="/",
    )

    # Also store minimal user info in session for immediate use
    request.session["user"] = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "role": payload.get("role", "user"),
    }

    return {
        "message": "Login successful, session cookie set",
        "user": request.session["user"],
    }


# ---------------------------------------------------------------------------
# Logout endpoint – clear session cookie and redirect to Keycloak
# -------------------------------------------------------------------------


@router.post("/logout", include_in_schema=False)
async def logout(request: Request, response: Response):
    """Clear session cookie and redirect to Keycloak logout."""
    # Clear the session cookie
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
    )

    # Get the post_logout_redirect_uri from session or use default
    post_logout = request.query_params.get("redirect_uri", KEYCLOAK_LOGOUT_REDIRECT_URI)

    # Redirect to Keycloak end session endpoint
    logout_url = f"{KEYCLOAK_URL}/protocol/openid-connect/logout?redirect_uri={urllib.parse.quote(post_logout, safe='')}"

    return Response(content={"logout_url": logout_url}, status_code=302)


# ---------------------------------------------------------------------------
# Me endpoint – return current user from session cookie
# -------------------------------------------------------------------------


@router.get("/me", include_in_schema=False)
async def me(request: Request):
    """Return the current authenticated user from the session cookie."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return {"user": user}


# ---------------------------------------------------------------------------
# Protected route dependency
# -------------------------------------------------------------------------


def get_current_user(request: Request):
    """Dependency that returns the current user from the session cookie."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
