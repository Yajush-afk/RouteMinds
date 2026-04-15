# Frontend Handoff

## New Stop Search Endpoint

Use the GTFS-native stop search endpoint instead of Nominatim:

- `GET /api/v1/stops/search?q=<query>&limit=<limit>`

Example response fields:

- `stop_id`
- `stop_name`
- `stop_lat`
- `stop_lon`
- `match_score`

Recommended use:

- use `stop_name` for dropdown display
- use `stop_id` for route optimization
- use `stop_lat` and `stop_lon` for marker placement and camera movement

## Expected Frontend Flow

1. user types origin stop query
2. frontend calls `/api/v1/stops/search`
3. user selects one stop result
4. user types destination stop query
5. frontend calls `/api/v1/stops/search`
6. user selects one stop result
7. frontend calls `POST /api/v1/routes/optimize`
8. frontend renders route and route summary from the route response

Prototype route flow no longer depends on Nominatim.

## Route Drawing Fields

Use the top-level `route_path_coordinates` field from the route response.

Each item contains:

- `stop_id`
- `lat`
- `lon`

Frontend should convert this into a GeoJSON `LineString` and draw the route as a
stop-to-stop polyline.

Fallback if needed:

- use the ordered `stops` array and each stop's `stop_lat` / `stop_lon`

## Route Summary Fields To Show First

Primary UI fields:

- `total_predicted_eta_minutes`
- `predicted_eta_lower_minutes`
- `predicted_eta_upper_minutes`
- `route_reliability_score`
- `total_wait_minutes`
- `congestion_proxy_percent`
- `explanation_summary`
- `selection_reasons`

Secondary details:

- `transfer_count`
- `fragile_transfer_count`
- `transfer_fragility_score`
- `service_quality_score`
- `cost_breakdown`
- `segments`

## Prototype Notes

- route API contract is frozen for prototype work
- backend route drawing support is already in place
- backend stop-resolution flow is now GTFS stop search -> route optimize
- if frontend integration exposes a backend bug, treat it as bug-fix-only work
