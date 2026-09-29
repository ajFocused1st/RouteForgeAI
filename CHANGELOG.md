# Changelog

All notable changes to RouteForge AI will be documented in this file.

## 2026-09-29

- Added production-readiness audit report mapping current implementation against `PROJECT_SPEC.md`.
- Added dependency audit documentation, removed the unnecessary Uvicorn standard extra, and moved frontend build tooling to devDependencies.
- Added security/privacy audit documentation, backend screenshot upload validation, frontend upload-size feedback, tighter CORS defaults, and focused security tests.
- Optimized the measured routing solver bottleneck by reducing the single-vehicle OR-Tools local-search cap to 100 ms and refreshed `docs/performance.md`.
- Added routing benchmark script and `docs/performance.md` results for 10, 25, 50, and 100 stop routing workloads.
- Added frontend workflow audit notes and fixed route draft stale-state handling, screenshot import clearing, Route History version listing, and route map text rendering.
- Added backend test audit notes and focused route optimization API failure tests for inactive route dependencies and capacity-exceeded version persistence.
- Added Tampa Bay development fixture with one depot, one 3,400 lb cargo van, ten schema-valid stops, and focused fixture validation tests.
- Added Windows `start-routeforge.bat` startup script with dependency checks, local provider checks, backend/frontend launch, browser open, and readable warnings/errors.
- Added Settings/System Health screen with provider status cards, local/external labels, and ONLINE/OFFLINE/MISSING/DISABLED state display.
- Added provider status service and `/api/status/providers` endpoint for backend, database, Ollama, Valhalla, geocoder, and local map/routing data checks.
- Added multi-vehicle dispatch optimization API and Dispatch UI with separate vehicle routes and multi-route map rendering.
- Added OR-Tools multi-vehicle optimizer with per-vehicle capacity, start/end depots, max hours, max mileage, and focused tests.
- Added AI route explanations grounded in RouteForge-calculated facts for deadhead, infeasibility, version changes, and shipment fit questions.
- Added Ask Dispatch AI panel with validated proposed changes and explicit apply/cancel controls before any supported route-state update.
- Added structured AI instruction parser that converts natural-language commands into validated proposed actions and rejects invalid AI output safely.
- Added local AI provider abstraction and Ollama implementation for command interpretation, result explanations, and structured change proposals without route or mileage calculation.
- Added standalone route economics engine for revenue, route and driver costs, contribution, per-mile metrics, and margin.
- Added CostProfile model and schemas for route costing fields with non-negative validation and persistence tests.
- Added deadhead mileage metrics for route optimization, including pre-pickup, between-job, post-delivery, return-to-depot, total unloaded mileage, and deadhead percentage.
- Added route version comparison API for miles, drive time, route time, stop order, and payload deltas.
- Added route version list/retrieve APIs and tests confirming each optimization creates a preserved `RouteVersion`.
- Connected the screenshot import workflow through extraction, review, address validation, starting location selection, optimization, and map rendering.
- Connected screenshot review confirmation to geocoding with normalized address results and explicit unresolved-address statuses before optimization.
- Added editable screenshot review table with customer, address, type, weight, time window, confidence, validation status, add/remove, and confirm controls.
- Added Ollama-backed local screenshot extraction provider with structured JSON schema validation, confidence handling, uncertainty preservation, and mocked tests.
- Added vision extraction provider architecture with an `ExtractedStop` schema and focused contract tests, without connecting vision to routing.
- Added screenshot import UI with drag/drop, file picker, clipboard paste, PNG/JPG/JPEG/WebP validation, and local preview without image understanding.
- Added backend-calculated route summary metrics and frontend Route Summary cards for miles, drive time, service time, duration, stops, payload, and remaining capacity.

## 2026-09-28

- Added MapLibre GL JS to the route screen with depot and numbered stop markers, popups, zoom-to-route, and backend geometry-driven route lines.
- Added route optimization API endpoint that validates routes, uses Valhalla matrices, runs OR-Tools, retrieves geometry, saves route versions, and returns metrics.
- Added time-window support to the single-vehicle optimizer for earliest/latest arrival, service duration, route start, required end time, and explicit infeasible results.
- Added vehicle payload capacity checks to the single-vehicle optimizer with focused tests for valid, overloaded, and invalid payload inputs.
- Added basic single-vehicle OR-Tools optimizer with deterministic matrix tests and no capacity/time-window constraints.
- Added routing matrix service with coordinate validation, provider-backed travel-time and distance matrices, persistent matrix caching, and focused tests.
- Added isolated Valhalla routing provider with health, matrix, route request support, Florida setup notes, and skip-safe integration tests.
- Added routing provider abstraction and schemas for travel-time matrices, distance matrices, route geometry, and route legs.
- Added persistent geocode cache model and service for normalized-address/provider lookup reuse.
- Added first OpenStreetMap-compatible Nominatim geocoder provider with rate limiting, caching, timeout/error handling, ambiguity handling, and mocked network tests.
- Added provider-based geocoding interface and `GeocodeResult` schema without a live geocoder implementation.
- Added frontend Route creation workspace with depot, vehicle, stop ordering, disabled optimization, and empty map panel.
- Added frontend Stops management screen connected to existing Stop APIs for list, create, edit, and deactivate workflows.
- Added frontend Vehicles screen connected to existing Vehicle APIs for list, create, edit, and deactivate workflows.
- Added route CRUD API endpoints with ordered stop assignment and focused API tests; optimization remains unimplemented.
- Added Stop CRUD API endpoints with structured responses, soft deactivate behavior, and focused API validation tests.
- Added Vehicle CRUD API endpoints with structured responses, soft deactivate behavior, and focused API tests.
- Added Depot CRUD API endpoints with structured responses, soft deactivate behavior, and focused API tests.
- Added Route, RouteStop, RouteVersion, and OptimizationRun models with focused tests for route timing metrics and preserved route versions.
- Added Stop SQLAlchemy model and Pydantic schemas with stop-type, coordinate, numeric, and time-window validation tests.
- Added Customer SQLAlchemy model and Pydantic schemas with focused validation and persistence tests.
- Added Vehicle SQLAlchemy model and Pydantic schemas with non-negative capacity validation and focused tests.
- Added Depot SQLAlchemy model and Pydantic schemas with focused persistence and validation tests.
- Added Vite React TypeScript frontend shell with sidebar navigation and backend health status display.
- Configured SQLite with SQLAlchemy database base, session helpers, startup initialization, and focused connectivity tests.
- Added minimum FastAPI backend with `/api/health`, structured JSON responses, settings, CORS, exception handling, and pytest configuration.
- Added RouteForge AI monorepo directory structure, including backend domain directories.
- Added `docs/environment-report.md` documenting installed tooling, missing or not-ready components, and setup recommendations.
- Added initial project documentation: `AGENTS.md`, `PROJECT_SPEC.md`, `TASKS.md`, and `CHANGELOG.md`.
