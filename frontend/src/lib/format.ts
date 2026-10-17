// Shared formatting utilities for display

/** Truncate a string to *maxLen* characters with an ellipsis. */
export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + "…";
}

/** Format an ISO timestamp for display. */
export function formatDate(ts: string): string {
  return new Date(ts).toLocaleString();
}