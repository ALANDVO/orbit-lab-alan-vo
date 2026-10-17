// Run list with filtering and pagination

import { formatDate, truncate } from "../lib/format";
import { stateBadgeClass } from "../lib/runState";
import type { Run, RunState } from "../api/types";

interface Props {
  runs: Run[];
  total: number;
  loading: boolean;
  error: string | null;
  filterState: RunState | "";
  filterAgent: string;
  onFilterChange: (state: RunState | "", agent: string) => void;
  onSelectRun: (run: Run) => void;
  onCancelRun: (run: Run) => void;
}

export function RunList({
  runs,
  total,
  loading,
  error,
  filterState,
  filterAgent,
  onFilterChange,
  onSelectRun,
  onCancelRun,
}: Props) {
  if (loading && runs.length === 0) {
    return <div className="loading-state">Loading runs…</div>;
  }

  if (error) {
    return <div className="error-state">Error: {error}</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="empty-state">
        No runs match your filters. Create one to get started.
      </div>
    );
  }

  return (
    <div className="run-list">
      <div className="run-list-filters">
        <select
          value={filterState}
          onChange={(e) => onFilterChange(e.target.value as RunState | "", filterAgent)}
        >
          <option value="">All states</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <input
          type="text"
          placeholder="Agent (e.g. codex)"
          value={filterAgent}
          onChange={(e) => onFilterChange(filterState, e.target.value)}
        />
      </div>

      <table className="run-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>State</th>
            <th>Repo</th>
            <th>Prompt</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>{run.agent}</td>
              <td>
                <span className={`state-badge ${stateBadgeClass[run.state]}`}>
                  {run.state}
                </span>
              </td>
              <td className="mono">{truncate(run.repo_url, 40)}</td>
              <td className="mono">{truncate(run.prompt, 60)}</td>
              <td>{formatDate(run.created_at)}</td>
              <td>
                <button
                  className="btn btn-small btn-secondary"
                  onClick={() => onSelectRun(run)}
                >
                  View
                </button>
                {(run.state === "pending" || run.state === "running") && (
                  <button
                    className="btn btn-small btn-danger"
                    onClick={() => onCancelRun(run)}
                  >
                    Cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="run-list-summary">
        Showing {runs.length} of {total} runs
      </div>
    </div>
  );
}