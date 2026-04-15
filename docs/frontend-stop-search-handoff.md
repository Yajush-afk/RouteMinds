# Frontend Stop Search Handoff

## Recommended Search Flow

For the RouteMinds prototype, frontend should stop using Nominatim for stop
search and instead use the GTFS-native stop search endpoint:

- `GET /api/v1/stops/search?q=<query>&limit=<limit>`

This endpoint searches Delhi bus stop names directly from GTFS static stop data.

## Prototype Search UX

Recommended frontend flow:

1. user types origin stop query
2. frontend calls `/api/v1/stops/search`
3. user selects a stop result
4. repeat for destination stop
5. frontend calls `/api/v1/routes/optimize` using selected `stop_id` values

## Suggested Fields To Use

Each stop search result returns:

- `stop_id`
- `stop_name`
- `stop_lat`
- `stop_lon`
- `match_score`

Frontend should use:

- `stop_name` for display
- `stop_id` for route optimization
- `stop_lat` and `stop_lon` for marker placement or camera movement

## Why This Is Better For The Prototype

- searches actual Delhi bus stops rather than general place names
- avoids external geocoding dependence
- aligns directly with the backend route optimization contract
- makes stop selection more deterministic for demos and judging
