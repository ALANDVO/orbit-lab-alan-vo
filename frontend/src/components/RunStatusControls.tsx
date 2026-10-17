// Status transition controls shown on the run detail page

import type { Run } from "../api/types";
import { StateBadge } from "./StateBadge";

interface Props {
  run: Run;
  onStart: () => void;
  onComplete: () => void;
  onFail: () => void;
  onCancel: () => void;
  error: string | null;
}

export function RunStatusControls({ run, onStart, onComplete, onFail, onCancel, error }: Props) {
  const isPending = run.state === "pending";
  const isRunning = run.state === "running";
  const isTerminal = !isPending && !isRunning;

  return (
    <div className="status-controls">
      <StateBadge state={run.state} />

      {isPending && (
        <>
          <button className="btn btn-small btn-primary" onClick={onStart}>
            Start
          </button>
          <button className="btn btn-small btn-danger" onClick={onCancel}>
            Cancel
          </button>
        </>
      )}

      {isRunning && (
        <>
          <button className="btn btn-small btn-success" onClick={onComplete}>
            Complete
          </button>
          <button className="btn btn-small btn-danger" onClick={onFail}>
            Fail
          </button>
          <button className="btn btn-small btn-danger" onClick={onCancel}>
            Cancel
          </button>
        </>
      )}

      {isTerminal && (
        <span className="terminal-label">Run finished — no further actions</span>
      )}

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}