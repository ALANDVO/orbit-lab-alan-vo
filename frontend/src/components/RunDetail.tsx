// Run detail view showing audit trail

import { formatDate } from "../lib/format";
import type { RunDetail } from "../api/types";
import { StateBadge } from "./StateBadge";

interface Props {
  detail: RunDetail | null;
  loading: boolean;
  error: string | null;
}

export function RunDetailView({ detail, loading, error }: Props) {
  if (loading) {
    return <div className="loading-state">Loading run…</div>;
  }

  if (error) {
    return <div className="error-state">Error: {error}</div>;
  }

  if (!detail) {
    return <div className="empty-state">No run selected.</div>;
  }

  const { run, audit } = detail;

  return (
    <div className="run-detail">
      <div className="run-detail-header">
        <h2>Run {run.id}</h2>
        <StateBadge state={run.state} />
      </div>

      <div className="run-detail-fields">
        <div className="field">
          <label>Agent</label>
          <span>{run.agent}</span>
        </div>
        <div className="field">
          <label>Repository</label>
          <span className="mono">{run.repo_url}</span>
        </div>
        {run.branch && (
          <div className="field">
            <label>Branch</label>
            <span>{run.branch}</span>
          </div>
        )}
        <div className="field">
          <label>Prompt</label>
          <pre className="prompt">{run.prompt}</pre>
        </div>
        <div className="field">
          <label>Worktree Path</label>
          <span className="mono">{run.worktree_path}</span>
        </div>
        {run.error_message && (
          <div className="field">
            <label>Error</label>
            <span className="error-text">{run.error_message}</span>
          </div>
        )}
        <div className="field">
          <label>Created</label>
          <span>{formatDate(run.created_at)}</span>
        </div>
        {run.started_at && (
          <div className="field">
            <label>Started</label>
            <span>{formatDate(run.started_at)}</span>
          </div>
        )}
        {run.finished_at && (
          <div className="field">
            <label>Finished</label>
            <span>{formatDate(run.finished_at)}</span>
          </div>
        )}
      </div>

      {audit.length > 0 && (
        <div className="audit-section">
          <h3>Audit Trail</h3>
          <table className="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((entry) => (
                <tr key={entry.id}>
                  <td>{formatDate(entry.timestamp)}</td>
                  <td><span className="mono">{entry.action}</span></td>
                  <td>{entry.actor}</td>
                  <td>{entry.detail ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}