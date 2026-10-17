/// <reference types="vitest/globals" />
import { render, screen } from "@testing-library/react";
import { RunList } from "./RunList";
import type { Run } from "../api/types";

const makeRun = (overrides: Partial<Run> = {}): Run => ({
  id: "test-run-id",
  agent: "codex",
  repo_url: "https://github.com/user/repo",
  branch: "main",
  prompt: "Fix the bug",
  worktree_path: "/tmp/orbit-worktrees/test",
  state: "pending",
  error_message: null,
  created_at: "2025-01-15T10:30:00Z",
  started_at: null,
  finished_at: null,
  updated_at: "2025-01-15T10:30:00Z",
  ...overrides,
});

describe("RunList", () => {
  const noop = vi.fn();

  it("shows loading state when loading and no runs", () => {
    render(
      <RunList
        runs={[]}
        total={0}
        loading={true}
        error={null}
        filterState=""
        filterAgent=""
        onFilterChange={noop}
        onSelectRun={noop}
        onCancelRun={noop}
      />
    );
    expect(screen.getByText(/loading runs/i)).toBeInTheDocument();
  });

  it("shows empty state when no runs and not loading", () => {
    render(
      <RunList
        runs={[]}
        total={0}
        loading={false}
        error={null}
        filterState=""
        filterAgent=""
        onFilterChange={noop}
        onSelectRun={noop}
        onCancelRun={noop}
      />
    );
    expect(screen.getByText(/no runs match/i)).toBeInTheDocument();
  });

  it("renders run rows with agent, state, and prompt", () => {
    const runs = [
      makeRun({ id: "run-1", agent: "codex", state: "pending" }),
      makeRun({ id: "run-2", agent: "claude-code", state: "running" }),
    ];
    render(
      <RunList
        runs={runs}
        total={2}
        loading={false}
        error={null}
        filterState=""
        filterAgent=""
        onFilterChange={noop}
        onSelectRun={noop}
        onCancelRun={noop}
      />
    );

    expect(screen.getByText("codex")).toBeInTheDocument();
    expect(screen.getByText("claude-code")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("Showing 2 of 2 runs")).toBeInTheDocument();
  });

  it("shows cancel button only for pending and running states", () => {
    const pendingRun = makeRun({ id: "pending-run", state: "pending" });
    const completedRun = makeRun({ id: "completed-run", state: "completed" });

    render(
      <RunList
        runs={[pendingRun, completedRun]}
        total={2}
        loading={false}
        error={null}
        filterState=""
        filterAgent=""
        onFilterChange={noop}
        onSelectRun={noop}
        onCancelRun={noop}
      />
    );

    const cancelButtons = screen.getAllByRole("button", { name: /cancel/i });
    expect(cancelButtons).toHaveLength(1);
  });
});