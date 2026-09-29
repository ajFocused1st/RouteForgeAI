# RouteForge AI Tasks

## Current Status

- Project documentation initialized.
- Application features have not been built yet.

## Task Log

| Date | Task | Status | Notes |
| --- | --- | --- | --- |
| 2026-09-29 | Production-readiness audit | Complete | Created `docs/release-readiness.md` classifying PROJECT_SPEC.md requirements as PASS, PARTIAL, FAIL, or NOT YET REQUIRED without modifying application code. |
| 2026-09-29 | Dependency audit | Complete | Reviewed backend and frontend dependencies, removed unnecessary `uvicorn[standard]` extra, moved frontend build tooling to devDependencies, refreshed the lockfile, and documented retained heavyweight libraries. |
| 2026-09-29 | Security/privacy audit | Complete | Audited external data flows, secrets, uploads, injection risks, AI tool access, and API exposure; added screenshot upload limits/type validation, tighter CORS defaults, focused tests, and audit documentation. |
| 2026-09-29 | Optimize verified routing bottleneck | Complete | Reduced the measured single-vehicle OR-Tools solver wait from roughly 1.0s to roughly 0.1s by tightening the existing local-search time limit, then reran benchmarks and focused tests. |
| 2026-09-29 | Benchmark routing | Complete | Added a repeatable routing benchmark script and recorded 10, 25, 50, and 100 stop matrix, solver, total request, and memory results in `docs/performance.md`. |
| 2026-09-29 | Run frontend workflow audit | Complete | Audited manual route creation, screenshot import, address review, optimization, route map, route history, and AI proposed changes; fixed stale route optimization state, screenshot clear behavior, Route History placeholder, and map text rendering. |
| 2026-09-29 | Run backend test audit | Complete | Reviewed backend tests, documented coverage gaps, and added focused route optimization API failure tests for inactive dependencies and payload-over-capacity version persistence. |
| 2026-09-29 | Create full integration fixture | Complete | Added a Tampa Bay development fixture with one depot, one 3,400 lb cargo van, ten stops, timed/priority/heavy/pickup scenarios, and schema validation tests. |
| 2026-09-29 | Create Windows startup script | Complete | Added `start-routeforge.bat` to check backend dependencies, SQLite, frontend dependencies, Ollama, and Valhalla, then launch backend/frontend and open the app with readable errors and warnings. |
| 2026-09-29 | Build Settings/System Health screen | Complete | Added Settings system health screen showing FastAPI, SQLite, Ollama, Valhalla, Geocoder, and Map data with ONLINE/OFFLINE/MISSING/DISABLED labels and LOCAL/EXTERNAL scope tags. |
| 2026-09-29 | Build provider status service | Complete | Added readable provider status checks for backend, database, Ollama, Valhalla, geocoder, and local map/routing data with a structured API endpoint and focused tests. |
| 2026-09-29 | Build multi-vehicle dispatch UI | Complete | Added a Dispatch screen with shared depot, multi-vehicle selection, stop selection, backend multi-vehicle optimization, separate vehicle route cards, and a multi-route map. |
| 2026-09-29 | Extend optimizer for multiple vehicles | Complete | Added OR-Tools multi-vehicle optimizer support for per-vehicle capacity, start depot, end depot, max hours, and max mileage with focused tests before UI changes. |
| 2026-09-29 | Add AI route explanations | Complete | Added AI route explanation endpoint and UI support for deadhead, infeasibility, version-change, and shipment-fit questions grounded in application-calculated metrics. |
| 2026-09-29 | Build AI Dispatcher UI | Complete | Added an Ask Dispatch AI route-workspace panel backed by validated instruction parsing, with proposed changes shown before explicit apply/cancel and no silent operational data changes. |
| 2026-09-29 | Build structured AI instruction parser | Complete | Added provider-backed natural-language instruction parsing into typed Pydantic proposed actions, including safe rejection of invalid AI output. |
| 2026-09-29 | Create local AI provider interface | Complete | Added AI provider abstraction and Ollama provider limited to command interpretation, result explanation, and structured change proposals without mileage or route calculation capabilities. |
| 2026-09-29 | Build route economics engine | Complete | Added a standalone route economics calculator for revenue, operating miles, route cost, driver cost, contribution, per-mile metrics, and margin without labeling contribution as accounting profit. |
| 2026-09-29 | Add CostProfile model | Complete | Added CostProfile SQLAlchemy model and schemas for operating cost, driver rate, tolls, parking, route expenses, and default service charge with non-negative validation and focused tests. |
| 2026-09-29 | Add deadhead calculations | Complete | Added separate deadhead calculation logic for pre-pickup, between-job, post-delivery, return-to-depot, total unloaded mileage, and deadhead percentage, with focused tests and route optimization metrics integration. |
| 2026-09-29 | Build route comparison | Complete | Added API support to compare two route versions across miles, drive time, route time, stop order, and payload with clear difference fields. |
| 2026-09-29 | Complete route versioning | Complete | Added route-version read schemas and API endpoints to list and retrieve preserved optimization versions; tests verify every optimization creates a new version. |
| 2026-09-29 | Connect screenshot-to-optimization workflow | Complete | Connected screenshot extraction, editable review, address validation, starting depot/vehicle selection, stop and route creation, optimization, and backend-geometry map rendering with an `OPTIMIZE FROM STARTING LOCATION` action. |
| 2026-09-29 | Connect screenshot import to geocoding | Complete | Added review-stop geocoding endpoint and frontend confirmation flow that normalizes/geocodes approved rows and marks low-confidence, ambiguous, not-found, or user-review-required addresses before optimization. |
| 2026-09-29 | Build screenshot review screen | Complete | Added an editable screenshot review table with add, edit, remove, and confirm controls plus validation status states, without fabricating extraction results. |
| 2026-09-29 | Add local screenshot extraction | Complete | Added an Ollama-backed local vision extraction provider using structured JSON schema validation, confidence scores, and no address guessing; tests mock local inference. |
| 2026-09-29 | Create vision provider architecture | Complete | Added `VisionExtractionProvider` and `ExtractedStop` schema for screenshot stop extraction without connecting vision to routing. |
| 2026-09-29 | Import from screenshot | Complete | Added a frontend screenshot import screen with drag/drop, file picker, clipboard paste, PNG/JPG/JPEG/WebP validation, and local image preview without image understanding. |
| 2026-09-29 | Display route metrics | Complete | Added backend-calculated route summary metrics for stops, payload, and remaining capacity, plus frontend Route Summary cards using optimization results. |
| 2026-09-28 | Add MapLibre | Complete | Integrated MapLibre GL JS into the route screen with depot and numbered stop markers, popups, zoom-to-route, and backend geometry-driven route lines. |
| 2026-09-28 | Add route optimization API | Complete | Added `POST /api/routes/{id}/optimize` to validate routes, retrieve routing matrices, run OR-Tools, request final geometry, calculate metrics, save route versions, and return complete optimization results. |
| 2026-09-28 | Add time windows | Complete | Extended the single-vehicle optimizer to enforce earliest/latest arrival, service duration, route start, and required end-time constraints with explicit infeasible-solution status. |
| 2026-09-28 | Add vehicle payload constraints | Complete | Extended the single-vehicle optimizer to validate stop weights and vehicle payload capacity, reject overloaded routes, and keep existing route solving unchanged. |
| 2026-09-28 | Build basic optimizer | Complete | Added single-vehicle OR-Tools optimizer for travel-time matrix and depot index with deterministic tests; no capacity or time-window constraints. |
| 2026-09-28 | Create routing matrix service | Complete | Added service that validates depot/stop coordinates, uses a routing provider for travel-time and distance matrices, caches ordered coordinate matrices, and includes focused tests. |
| 2026-09-28 | Set up Valhalla | Complete | Added isolated Valhalla `RoutingProvider` implementation with health, matrix, route geometry, route legs, Florida setup docs, unit tests, and skip-safe integration tests. |
| 2026-09-28 | Create routing provider abstraction | Complete | Added `RoutingProvider` protocol, routing schemas for travel-time matrix, distance matrix, route geometry, and route legs, plus focused tests. |
| 2026-09-28 | Add geocode cache | Complete | Added persistent `GeocodeCache` model and cache service to avoid repeated provider lookups for identical normalized addresses, with focused tests. |
| 2026-09-28 | Implement first geocoder | Complete | Added configurable Nominatim provider with normalization, rate limiting, caching, timeout/error handling, ambiguity handling, and mocked network tests. |
| 2026-09-28 | Create geocoding provider interface | Complete | Added provider protocol, `GeocodeResult` schema with confidence/status fields, exports, and focused tests without a live provider. |
| 2026-09-28 | Build Route creation screen | Complete | Added frontend route workspace with route name, depot and vehicle selection, stop assignment, ordered stop table, disabled optimization button, and empty map panel. |
| 2026-09-28 | Build Stops screen | Complete | Added frontend Stops management screen connected to Stop APIs for list, create, edit, and deactivate workflows. |
| 2026-09-28 | Build Vehicles screen | Complete | Added frontend Vehicles screen connected to Vehicle APIs for list, create, edit, and deactivate workflows. |
| 2026-09-28 | Build route CRUD | Complete | Added route creation, listing, retrieval, update, stop assignment, and focused API tests without optimization. |
| 2026-09-28 | Build Stop API | Complete | Added Stop CRUD endpoints with soft deactivate behavior, frontend-readable validation errors, and focused API tests. |
| 2026-09-28 | Build Vehicle API | Complete | Added Vehicle CRUD endpoints with soft deactivate behavior and focused API tests. |
| 2026-09-28 | Build Depot API | Complete | Added Depot CRUD endpoints with soft deactivate behavior and focused API tests. |
| 2026-09-28 | Create Route models | Complete | Added Route, RouteStop, RouteVersion, and OptimizationRun models with route metrics fields and version-preservation tests. |
| 2026-09-28 | Create Stop model | Complete | Added Stop SQLAlchemy model, Pydantic schemas, stop-type and field validation, metadata registration, and focused tests. |
| 2026-09-28 | Create Customer model | Complete | Added Customer SQLAlchemy model, Pydantic schemas, metadata registration, and focused tests. |
| 2026-09-28 | Create Vehicle model | Complete | Added Vehicle SQLAlchemy model, Pydantic schemas, non-negative capacity validation, metadata registration, and focused tests. |
| 2026-09-28 | Create Depot model | Complete | Added Depot SQLAlchemy model, Pydantic schemas, metadata registration, and focused model/schema tests. |
| 2026-09-28 | Create Vite React frontend shell | Complete | Added React + TypeScript + Vite app shell with sidebar navigation and `/api/health` backend status check. |
| 2026-09-28 | Configure SQLite with SQLAlchemy | Complete | Added configurable database URL, declarative base, session management, startup initialization, and connectivity tests. |
| 2026-09-28 | Create minimum FastAPI backend | Complete | Added app factory, health endpoint, structured responses, exception handlers, settings, CORS, and pytest health test. |
| 2026-09-28 | Create monorepo directory structure | Complete | Added root project directories and backend domain directories without business functionality. |
| 2026-09-28 | Verify development environment | Complete | Added `docs/environment-report.md` with installed, missing, and recommended environment notes. |
| 2026-09-28 | Create initial project documentation files | Complete | Added `AGENTS.md`, `PROJECT_SPEC.md`, `TASKS.md`, and `CHANGELOG.md`. |

## Backlog

- Define initial repository structure when implementation begins.
- Create React + TypeScript + Vite frontend when requested.
- Create FastAPI backend when requested.
- Define SQLite and SQLAlchemy data model when requested.
- Plan Valhalla, OpenStreetMap, MapLibre, OR-Tools, and Ollama integration boundaries when requested.
