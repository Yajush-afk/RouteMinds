# Prototype Backend Contract

## Purpose

This document freezes the backend contract for the RouteMinds prototype. From
this point onward, backend changes should be limited to bug fixes unless a
frontend integration issue forces a small additive update.

## Stable Prototype Flow

The prototype route flow is:

1. frontend resolves origin and destination places to latitude/longitude
2. frontend calls `GET /api/v1/stops/nearby` for each side
3. frontend selects the nearest valid stop for origin and destination
4. frontend calls `POST /api/v1/routes/optimize` with those stop IDs
5. frontend draws the returned route using the ordered `stops` coordinates
6. frontend shows ETA, ETA range, reliability, wait, congestion proxy, and
   explanation fields from the route response

For the prototype, the stop-resolution rule is intentionally simple:

- use the nearest returned stop as the selected stop for each side

## Route Drawing Contract

The prototype does not require backend-generated geometry.

Frontend route drawing should use:

- the ordered `stops` array in the route response
- each stop's `stop_lat` and `stop_lon`

This means the first route visualization is a stop-to-stop polyline. That is
acceptable for the prototype and avoids unnecessary backend geometry work.

## Stable Route Response Fields

Frontend may rely on these top-level route fields:

- `stops`
- `segments`
- `total_predicted_eta_minutes`
- `predicted_eta_lower_minutes`
- `predicted_eta_upper_minutes`
- `route_reliability_score`
- `generalized_cost_minutes`
- `total_wait_minutes`
- `total_in_vehicle_minutes`
- `transfer_count`
- `fragile_transfer_count`
- `transfer_fragility_score`
- `congestion_proxy_ratio`
- `congestion_proxy_percent`
- `service_quality_score`
- `selection_reasons`
- `explanation_summary`
- `cost_breakdown`
- `alternatives`

Frontend may rely on these segment fields:

- route/stop identity fields
- scheduled and expected wait fields
- transfer fragility fields
- uncertainty and reliability fields
- penalty breakdown fields
- congestion proxy fields
- corridor instability and service-quality fields

## Fields To Prioritize In UI

The first prototype UI should emphasize:

- `total_predicted_eta_minutes`
- `predicted_eta_lower_minutes`
- `predicted_eta_upper_minutes`
- `route_reliability_score`
- `total_wait_minutes`
- `congestion_proxy_percent`
- `explanation_summary`
- `selection_reasons`

The following can be placed in a secondary details panel:

- `transfer_fragility_score`
- `cost_breakdown`
- segment-level penalty fields
- `service_quality_score`

## Deferred Work

The following are explicitly deferred and must not block the prototype:

- full RT-dataset retrained production model
- weather-integrated model training
- explicit road-context model retraining
- full-network GTFS-RT reconstruction coverage
- backend-generated route geometry
- route alternatives beyond placeholder support

## Backend Policy

Prototype backend work from this point is limited to:

- bug fixes
- integration blockers discovered by frontend wiring
- additive explanation polish only when necessary
