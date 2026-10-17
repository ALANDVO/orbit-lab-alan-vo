/**
 * TypeScript types derived from backend API schemas.
 * Mirrors the Pydantic models in backend/app/schemas/run.py.
 */

export type RunState = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface Run {
  id: string;
  agent: string;
  repo_url: string;
  branch: string | null;
  prompt: string;
  worktree_path: string;
  state: RunState;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
}

export interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  detail: string | null;
  timestamp: string;
}

export interface RunDetail {
  run: Run;
  audit: AuditEntry[];
}

export interface RunListResponse {
  runs: Run[];
  limit: number;
  offset: number;
  total: number;
}

export interface RunCreate {
  agent: string;
  repo_url: string;
  prompt: string;
  branch?: string | null;
}

export interface ErrorResponse {
  detail: string;
}