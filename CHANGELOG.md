# Changelog

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

### Planned (future milestones)
- OIDC authentication via Keycloak (viewer/operator/admin roles)
- LLM provider adapters (OpenAI-compatible, Anthropic, Gemini, Ollama)
- Run execution engine (actual agent spawning with worktree creation)
- Diff annotation workflow
- Mobile companion integration