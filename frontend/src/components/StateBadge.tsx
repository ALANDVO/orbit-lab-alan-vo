// Display a colored badge for run state

import { stateBadgeClass, stateLabel } from "../lib/runState";
import type { RunState } from "../api/types";

interface Props {
  state: RunState;
}

export function StateBadge({ state }: Props) {
  return (
    <span className={`state-badge ${stateBadgeClass[state]}`}>{stateLabel[state]}</span>
  );
}