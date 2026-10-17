// Typed API client matching backend routes in app/api/runs.py.
// All endpoints derive from the actual FastAPI routes. Errors are returned
// as ApiError with the backend's detail string.

import type { RunCreate, RunDetail, RunListResponse, Run, ErrorResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

class ApiError extends Error {
  constructor(public status: number, public body: ErrorResponse) {
    super(`API ${status}: ${body.detail}`);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!resp.ok) {
    const body: ErrorResponse = await resp.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(resp.status, body);
  }
  return resp.json();
}

export const api = {
  /** POST /api/runs — create a new agent run. */
  createRun: (payload: RunCreate) =>
    apiFetch<Run>("/runs/", { method: "POST", body: JSON.stringify(payload) }),

  /** GET /api/runs — list runs with optional filtering/pagination. */
  listRuns: (opts?: { state?: string; agent?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams();
    if (opts?.state) params.set("state", opts.state);
    if (opts?.agent) params.set("agent", opts.agent);
    if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts?.offset !== undefined) params.set("offset", String(opts.offset));
    const qs = params.toString();
    const path = qs ? `/runs/?${qs}` : "/runs/";
    return apiFetch<RunListResponse>(path, { method: "GET" });
  },

  /** GET /api/runs/{id} — get a run with its audit trail. */
  getRun: (runId: string) =>
    apiFetch<RunDetail>(`/runs/${runId}`, { method: "GET" }),

  /** DELETE /api/runs/{id} — cancel a pending or running run. */
  cancelRun: (runId: string) =>
    apiFetch<Run>(`/runs/${runId}`, { method: "DELETE" }),

  /** POST /api/runs/{id}/start — transition run to running. */
  startRun: (runId: string) =>
    apiFetch<Run>(`/runs/${runId}/start`, { method: "POST" }),

  /** POST /api/runs/{id}/complete — transition run to completed. */
  completeRun: (runId: string) =>
    apiFetch<Run>(`/runs/${runId}/complete`, { method: "POST" }),

  /** POST /api/runs/{id}/fail?error_message=... — transition run to failed. */
  failRun: (runId: string, errorMessage: string) =>
    apiFetch<Run>(`/runs/${runId}/fail?error_message=${encodeURIComponent(errorMessage)}`, { method: "POST" }),

  /** GET /health — health check. */
  health: () =>
    apiFetch<{ status: string; service: string; version: string }>("/health", { method: "GET" }),
};

export type { ApiError };