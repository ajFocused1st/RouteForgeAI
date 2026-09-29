# Security And Privacy Audit

Date: 2026-09-29

## Data Sent Externally

- Geocoding sends reviewed addresses to the configured Nominatim-compatible geocoder. The default is `https://nominatim.openstreetmap.org`.
- MapLibre fetches map tiles from `https://tile.openstreetmap.org` in the frontend map style.
- Valhalla requests are configured for `http://127.0.0.1:8002` by default and are intended to stay local.
- Ollama AI and vision requests are configured for `http://127.0.0.1:11434` by default and are intended to stay local. Screenshot image bytes are sent to that provider when extraction is requested.

## Exposed Secrets

- No committed API keys, bearer tokens, passwords, private keys, or secret files were found in the audited source paths.
- `routeforge.db` is a local SQLite database file and may contain operational route data. It should remain local and should not be committed or shared.

## High-Priority Fixes Applied

- Added backend screenshot content-type validation for `/api/vision/extract`.
- Added backend screenshot size enforcement before invoking the vision provider.
- Added frontend screenshot size feedback to match the backend limit.
- Tightened CORS defaults to local configured origins, explicit methods, explicit `Content-Type` header, and no credentialed browser requests.

## Injection And AI Tool Risk

- Database access uses SQLAlchemy ORM/query construction for user-controlled CRUD paths. No user-controlled SQL string execution was found.
- Frontend rendering uses React text rendering and MapLibre popup DOM `textContent`, not raw HTML insertion, for audited user-controlled display fields.
- AI providers do not receive tool execution capability. AI output is parsed through Pydantic schemas, proposed changes require explicit user confirmation, and unsupported proposed actions are rejected rather than executed.

## Remaining Privacy Notes

- The default geocoder and map tiles are external OpenStreetMap services. For fully offline privacy, configure local geocoding and local tile hosting before using sensitive customer data.
- This is a local-first app without user authentication. Keep the backend bound to trusted local networks only unless an explicit access-control layer is added later.
