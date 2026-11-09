# Changelog

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added
- **Frontend Execute button** — Added "Execute" button to run detail page for pending runs, connecting the existing backend execution endpoint (`POST /api/runs/{id}/execute`) to the UI. Includes `executeRun` API client function and updated `RunStatusControls` component.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Orbit Lab are documented here.

## [1.0.0] — 2025-01-15

### Added
- **Agent Run Management** — API to create, list (with filtering and pagination), view details, and cancel agent runs
- **Worktree allocation engine** — deterministic, content-derived worktree paths from repository URL and run ID with collision detection and path-traversal protection
- **Run lifecycle state machine** — enforces valid transitions: `pending → running → completed/failed/cancelled`, rejects invalid transitions with 409 Conflict
- **Audit log** — every mutation (create, state change, cancel, delete) recorded with UTC timestamp and actor context
- **SQLite persistence** — SQLAlchemy-backed storage with persistent records, UTC timestamps, and transactional mutations
- **React frontend** — dashboard with create-run form, run list with filtering, and run detail view showing the full audit trail
- **Typed API client** — TypeScript client derived from actual FastAPI route schemas
- **Docker support** — multi-stage Dockerfiles for backend and frontend with nonroot users, healthchecks, and compose.yaml
- **CI pipeline** — backend pytest, frontend typecheck/build/test, and Docker build checks
- **61 backend tests** covering domain logic (allocation uniqueness, state machine transitions, audit logging), API boundary tests, and HTTP integration
- **15 frontend tests** covering user-visible behavior (state badges, form submission, run list rendering)

### Fixed
- **Worktree base directory validation** — `worktree_base_dir()` now validates the `ORBIT_WORKTREE_BASE` environment variable, ensuring it's an absolute path and falling back to the default when empty
- **Worktree path validation** — `validate_worktree_path()` now correctly accepts the base directory itself as valid, not just subdirectories

### Planned (future milestones)
- OIDC authentication via Keycloak (viewer/operator/admin roles)
- LLM provider adapters (OpenAI-compatible, Anthropic, Gemini, Ollama)
- Run execution engine (actual agent spawning with worktree creation)
- Diff annotation workflow
- Mobile companion integration

## [1.1.0] — 2025-11-05

### Added
- **Agent Run Execution Engine** — Service that spawns isolated git worktrees for agent runs, executes agent processes, and tracks execution state
- **WebSocket streaming endpoint** — `GET /api/runs/{id}/stream` provides real-time stdout/stderr streaming from running agents
- **Execute API endpoint** — `POST /api/runs/{id}/execute` triggers full execution lifecycle (worktree creation → agent spawn → completion)
- **Execution tracking fields** — Added `pid`, `exit_code`, and `duration_seconds` to Run model for monitoring agent runs
- **Git worktree isolation** — Each run gets a dedicated branch (`orbit-{run_id}`) in a separate worktree directory
- **Local repository support** — Execution service handles both remote URLs and local repository paths
- **Comprehensive test coverage** — 9 new tests for execution service covering worktree preparation, execution success/failure, cancellation, and state validation

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
