# Backend Test Audit

Date: 2026-09-29

## Scope

Reviewed backend-only pytest coverage across API endpoints, schemas, database setup, routing, geocoding, optimization, economics, AI, vision, provider status, and the development fixture.

## Findings

- Core backend models and schemas are well covered for happy paths and basic validation.
- CRUD APIs have consistent coverage for create, list, retrieve, update, deactivate, unknown records, and common validation errors.
- Optimization has strong unit coverage for single-vehicle and multi-vehicle constraints, but API-level optimization guard coverage was missing for inactive route dependencies and payload-over-capacity version persistence.
- Routing, geocoding, Valhalla, Ollama, vision, provider status, route economics, deadhead, and fixture tests are focused and mostly isolated with mocked or skip-safe external dependencies.
- Some API tests duplicate CRUD response-shape checks across resource types. This is acceptable for now because the surface area is small and the repetition keeps failures easy to read.
- Tests that assert exact response dictionaries are somewhat brittle if the shared error envelope changes, but they also protect frontend-facing response contracts.

## Added Tests

- Route optimization rejects inactive depots.
- Route optimization rejects inactive vehicles.
- Route optimization rejects inactive stops.
- Route optimization saves a failed `RouteVersion` when vehicle payload capacity is exceeded.

## Remaining High-Value Gaps

- Route optimization provider failures could use more API tests for upstream routing errors and malformed provider responses.
- Dispatch optimization could use more failure-path API coverage for invalid vehicle/stop/depot references.
- AI explanation endpoints are grounded in calculated facts, but more negative tests around missing route versions or incomplete metrics would reduce regression risk.
