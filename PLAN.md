# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

agent-runs

## Roadmap

### agent-runs — Agent Run Management

Status: done

Acceptance:
- POST /api/runs creates a run with prompt, agent, and worktree allocation; returns run with unique ID, state, and worktree path
- GET /api/runs lists runs with pagination and filtering by state and agent
- GET /api/runs/{id} returns run details including audit log entries
- DELETE /api/runs/{id} cancels a pending/running run; returns updated state
- Worktree allocation produces deterministic unique paths; duplicate repo prompts are distinguished by run suffix
- Run lifecycle enforces valid state transitions (pending -> running -> completed/failed/cancelled)
- All mutations are audited with UTC timestamps and user context

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/models/run.py`, `backend/app/models/audit.py`, `backend/app/schemas/run.py`, `backend/app/services/worktree.py`, `backend/app/services/run.py`, `backend/app/api/runs.py`, `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/hooks/useRuns.ts`, `frontend/src/components/RunList.tsx`, `frontend/src/components/RunForm.tsx`, `frontend/src/components/RunDetail.tsx`, `frontend/src/components/RunStatusControls.tsx`, `frontend/src/components/StateBadge.tsx`, `frontend/src/pages/RunsPage.tsx`, `frontend/src/pages/RunDetailPage.tsx`, `frontend/src/lib/format.ts`, `frontend/src/lib/runState.ts`

Tests: `backend/tests/test_worktree_service.py`, `backend/tests/test_run_service.py`, `backend/tests/test_api_runs.py`, `backend/tests/conftest.py`, `frontend/src/components/RunList.test.tsx`, `frontend/src/components/RunForm.test.tsx`, `frontend/src/components/StateBadge.test.tsx`

### run-execution — Agent Run Execution Engine

Status: planned

Acceptance:
- Service spawns isolated git worktree for the agent run
- Backend streams agent stdout/stderr via WebSocket
- Agent completion updates run state and records duration

### auth-oidc — OIDC Authentication

Status: planned

Acceptance:
- Backend-managed sessions with HttpOnly SameSite cookies
- Keycloak integration with state + nonce + PKCE
- Role-based authorization (viewer/operator/admin) on all endpoints

### llm-adapters — LLM Provider Adapters

Status: planned

Acceptance:
- OpenAI-compatible adapter (OpenAI, LiteLLM, OpenRouter, Ollama)
- Anthropic messages adapter
- Gemini generateContent adapter
- Advisory LLM explanations opt-in per run

### agent-diff — Annotate AI Diffs

Status: planned

Acceptance:
- Comment on diff lines from agent runs
- Send feedback back to agent prompt
- Track resolution status

