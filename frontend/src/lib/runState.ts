// Run state styling utilities

import type { RunState } from "../api/types";

export const stateBadgeClass: Record<RunState, string> = {
  pending: "badge-pending",
  running: "badge-running",
  completed: "badge-completed",
  failed: "badge-failed",
  cancelled: "badge-cancelled",
};

export const stateLabel: Record<RunState, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};