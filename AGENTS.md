# AGENTS.md

Guidance for Codex and other coding agents working on RouteForge AI.

## Project Posture

RouteForge AI is a local-first route planning and optimization application. The intended architecture is:

- React + TypeScript + Vite frontend
- FastAPI backend
- SQLite local database
- SQLAlchemy ORM and migrations where appropriate
- OR-Tools for optimization
- Valhalla for routing
- OpenStreetMap data
- MapLibre for map rendering
- Ollama for local AI assistance
- Local-first operation
- No required Google Maps APIs

Do not build application features until they are explicitly requested.

## Working Rules

- Inspect only files relevant to the current task.
- Preserve working code and existing behavior.
- Make the smallest complete change that satisfies the request.
- Avoid unrelated refactors, formatting churn, dependency changes, and architecture rewrites.
- Do not add fake, mock, demo, placeholder, or simulated functionality unless explicitly requested.
- Prefer real integrations and clearly documented incomplete work over pretend behavior.
- Keep changes scoped to the requested task and the established architecture.
- Run focused tests that cover the changed behavior when tests exist or can be added appropriately.
- If tests cannot be run, explain why in the final response.
- Update `TASKS.md` after completing a task.
- Add a concise entry to `CHANGELOG.md` for completed changes.

## Implementation Preferences

- Follow existing project patterns once code exists.
- Keep frontend, backend, database, routing, optimization, map, and local AI concerns separated.
- Avoid introducing required cloud services for core workflows.
- Do not require Google Maps APIs for routing, geocoding, map rendering, or optimization.
- Favor explicit local configuration over hidden global state.
- Keep user data local by default.

## Completion Checklist

Before finishing a task:

- Confirm the requested scope was handled.
- Confirm unrelated files were not changed.
- Run focused tests or document why they were not run.
- Update `TASKS.md` with the task status.
- Add a concise `CHANGELOG.md` entry.
