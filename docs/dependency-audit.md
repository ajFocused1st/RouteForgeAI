# Dependency Audit

Date: 2026-09-29

## Backend

- Kept `fastapi`: used by the API application, routers, middleware, and tests.
- Kept `sqlalchemy`: used by database setup, models, API queries, and services.
- Kept `pydantic-settings`: used by runtime settings.
- Kept `ortools`: used by single-vehicle and multi-vehicle optimization.
- Kept `uvicorn`, but removed the `standard` extra. The startup script uses `python -m uvicorn`, and the current app does not require the extra WebSocket/watch/reload/performance packages.
- Kept `pytest` and `httpx` as development dependencies for the test suite and FastAPI `TestClient`.

## Frontend

- Kept runtime dependencies `react`, `react-dom`, and `maplibre-gl`; all are imported by the application.
- Moved `@vitejs/plugin-react`, `typescript`, and `vite` to `devDependencies` because they are build/dev-server tooling, not runtime application packages.
- Kept React type packages in `devDependencies`.

## Not Removed

- `maplibre-gl` is heavyweight, but it is the active map renderer and replacing it would be speculative.
- `ortools` is heavyweight, but it is the active optimizer and required by existing backend behavior.
