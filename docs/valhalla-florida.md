# Valhalla Florida Setup

RouteForge AI expects the first Valhalla routing provider to use Florida OpenStreetMap data for development.

Default local settings:

- `ROUTEFORGE_VALHALLA_URL=http://127.0.0.1:8002`
- `ROUTEFORGE_VALHALLA_COSTING=auto`
- `ROUTEFORGE_VALHALLA_OSM_REGION=florida`

This step adds the provider integration only. It does not download map data, build Valhalla tiles, start Docker, or connect route optimization.
