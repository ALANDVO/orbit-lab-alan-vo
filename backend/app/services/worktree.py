"""Worktree allocation engine.

Given a repository URL and a unique run ID, produces a deterministic, unique
worktree path. Handles collisions by appending a short suffix.
"""
from __future__ import annotations

import hashlib
import os
import re


def repo_slug(repo_url: str) -> str:
    """Extract a filesystem-safe slug from a repository URL."""
    # Strip protocol prefix
    slug = re.sub(r"^.*://", "", repo_url)
    # Strip leading user@host: for SCP-like URLs
    slug = re.sub(r"^.*@", "", slug)
    # Strip .git suffix and path separators
    slug = slug.removesuffix(".git")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-").lower()
    return slug or "repo"


def worktree_base_dir() -> str:
    """Base directory for worktrees — configurable via env."""
    base = os.environ.get("ORBIT_WORKTREE_BASE", "/tmp/orbit-worktrees")
    if not base:
        base = "/tmp/orbit-worktrees"
    # Ensure absolute path
    return os.path.abspath(base)


def allocate_worktree_path(run_id: str, repo_url: str, existing: set[str] | None = None) -> str:
    """Allocate a unique, deterministic worktree path for a run.

    The path is derived from the repo slug and a short hash of the run ID,
    ensuring determinism. If a collision is detected (via the *existing* set),
    a numeric suffix is appended.

    Args:
        run_id: Unique identifier for the run.
        repo_url: Git remote URL of the repository.
        existing: Optional set of paths already in use (for collision detection).

    Returns:
        An absolute path string guaranteed unique given *existing*.
    """
    existing = existing or set()
    slug = repo_slug(repo_url)
    # Short deterministic hash of run ID for distinguishing duplicate repo prompts
    short_hash = hashlib.sha256(run_id.encode()).hexdigest()[:8]
    base_name = f"{slug}-{short_hash}"
    base_path = os.path.join(worktree_base_dir(), base_name)

    if base_path not in existing and base_path != "":
        return base_path

    # Collision: append incrementing suffix
    counter = 1
    while True:
        candidate = f"{base_path}-{counter}"
        if candidate not in existing and candidate != "":
            return candidate
        counter += 1


def validate_worktree_path(path: str) -> bool:
    """Validate that a worktree path is within the base directory and safe."""
    base = worktree_base_dir()
    # Resolve to absolute and check it's under base
    abs_path = os.path.abspath(path)
    abs_base = os.path.abspath(base)
    # Must be within base directory (prevent path traversal)
    # Allow the base directory itself as valid
    if abs_path == abs_base:
        return True
    if not abs_path.startswith(abs_base + os.sep):
        return False
    # Must not contain traversal components
    if ".." in path:
        return False
    return True


def run_worktree_dir(run_id: str) -> str:
    """Return the dedicated worktree directory for a run (without repo slug).

    Used to locate a run's worktree for status checks or cleanup.
    """
    short_hash = hashlib.sha256(run_id.encode()).hexdigest()[:8]
    return os.path.join(worktree_base_dir(), f"run-{short_hash}")