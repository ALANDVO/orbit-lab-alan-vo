"""Tests for the worktree allocation engine."""
from __future__ import annotations

import os

import pytest

from app.services.worktree import (
    allocate_worktree_path,
    repo_slug,
    run_worktree_dir,
    validate_worktree_path,
    worktree_base_dir,
)


class TestRepoSlug:
    def test_strips_protocol(self):
        assert repo_slug("https://github.com/alandvo/orbit-lab-alan-vo") == "github-com-alandvo-orbit-lab-alan-vo"

    def test_strips_git_suffix(self):
        assert repo_slug("https://github.com/user/repo.git") == "github-com-user-repo"

    def test_strips_scp_prefix(self):
        assert repo_slug("git@github.com:user/repo.git") == "github-com-user-repo"

    def test_handles_ssh_url(self):
        assert repo_slug("ssh://git@github.com/user/repo.git") == "github-com-user-repo"

    def test_empty_url_fallback(self):
        assert repo_slug("") == "repo"

    def test_local_path_preserves_segments(self):
        assert repo_slug("/home/user/projects/my-repo") == "home-user-projects-my-repo"


class TestAllocateWorktreePath:
    def test_deterministic_same_input(self):
        path1 = allocate_worktree_path("run-1", "https://github.com/user/repo")
        path2 = allocate_worktree_path("run-1", "https://github.com/user/repo")
        assert path1 == path2

    def test_different_run_ids_differ(self):
        path1 = allocate_worktree_path("run-1", "https://github.com/user/repo")
        path2 = allocate_worktree_path("run-2", "https://github.com/user/repo")
        assert path1 != path2

    def test_collision_appends_suffix(self):
        """When the generated path is already in existing, a suffix is appended."""
        base = allocate_worktree_path("run-1", "https://github.com/user/repo")
        # Pass same run_id + repo so the generated path equals base, forcing a collision
        collision = allocate_worktree_path(
            "run-1",
            "https://github.com/user/repo",
            existing={base},
        )
        assert collision != base
        assert collision.endswith("-1")

    def test_second_collision_increments(self):
        base = allocate_worktree_path("run-1", "https://github.com/user/repo")
        first = allocate_worktree_path("run-1", "https://github.com/user/repo", existing={base})
        second = allocate_worktree_path("run-1", "https://github.com/user/repo", existing={base, first})
        assert second.endswith("-2")

    def test_path_within_base_dir(self):
        path = allocate_worktree_path("run-1", "https://github.com/user/repo")
        base = worktree_base_dir()
        assert path.startswith(base)


class TestValidateWorktreePath:
    def test_accepts_valid_path(self):
        path = os.path.join(worktree_base_dir(), "valid-path")
        assert validate_worktree_path(path) is True

    def test_rejects_traversal(self):
        path = os.path.join(worktree_base_dir(), "..", "escape")
        assert validate_worktree_path(path) is False

    def test_rejects_absolute_outside_base(self):
        assert validate_worktree_path("/etc/passwd") is False

    def test_rejects_traversal_string(self):
        assert validate_worktree_path("/tmp/escape/../etc") is False


class TestRunWorktreeDir:
    def test_deterministic(self):
        dir1 = run_worktree_dir("run-1")
        dir2 = run_worktree_dir("run-1")
        assert dir1 == dir2

    def test_different_ids_differ(self):
        dir1 = run_worktree_dir("run-1")
        dir2 = run_worktree_dir("run-2")
        assert dir1 != dir2