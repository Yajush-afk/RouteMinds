# Backend Alignment Phase 1: Data And Contract Audit

## Purpose

Phase 1 converts the Phase 0 alignment spec into concrete backend contracts.
This phase still does not change runtime behavior. It locks the exact contract
changes needed for training, inference, routing, and API responses so that later
phases can be implemented consistently.

The outcome of this phase is a file-by-file implementation map for the rest of
`backend/alignment`.

## Current Backend Contract Snapshot

The current backend contracts are intentionally narrow:

- training target: `actual_segment_minutes`
- prediction API output:
  - `predicted_actual_segment_minutes`
  - `predicted_segment_delay_minutes`
- route API output:
  - stop path
  - segment list with wait and predicted travel time
  - `total_predicted_eta_minutes`
- routing cost model:
  - boarding wait
  - predicted in-vehicle travel time
  - fixed transfer buffer

The current backend does not yet expose:

- segment uncertainty
- segment reliability score
- congestion proxy fields
- generalized route cost breakdown
- explanation metadata
- alternative route summaries

## Feature Contract V2

Feature contract v2 preserves the current core features and expands them in a
controlled way.

### Existing Core Segment Features To Keep

- `route_id`
- `from_stop_id`
- `to_stop_id`
- `stop_sequence`
- `normalized_stop_position`
- `distance_to_prev_stop_km`
- `segment_start_scheduled_unix`
- `scheduled_segment_minutes`
- `prev_segment_delay`
- `rolling_segment_delay_3`

### New Feature Families To Add Later

These are not implemented in Phase 1, but they are now part of the locked
contract for future phases.

#### Transit And Operational Context

- `hour_of_day`
- `day_of_week`
- `direction_id` when derivable from GTFS
- route-progress bucket derived from `stop_sequence` and
  `normalized_stop_position`

#### Realtime Operational Proxies

- `route_delay_minutes_live`
- `segment_slowdown_ratio_live`
- `corridor_slowdown_score_live`
- `bunching_score_live`
- `headway_irregularity_score_live`
- `stop_recent_arrival_gap_minutes`

#### Waiting And Transfer Features

- `expected_wait_minutes`
- `boarding_feasibility_score`
- `transfer_slack_minutes`
- `transfer_fragility_score`

#### Road-Context Features

- `road_hierarchy`
- `intersection_density`
- `junction_complexity_score`
- `corridor_risk_tag`
- `signal_density_proxy`

#### Optional Weather Features

Weather is explicitly optional and should not block the alignment branch.

- `weather_rainfall_mm`
- `weather_temperature_c`
- `weather_is_adverse`

## Prediction Output Contract V2

### Current Output

The current prediction output is:

- `predicted_actual_segment_minutes`
- `predicted_segment_delay_minutes`

### Locked V2 Output

The prediction layer must grow to this shape:

- `predicted_actual_segment_minutes`
- `predicted_segment_delay_minutes`
- `segment_uncertainty`
- `segment_reliability_score`
- `congestion_proxy_ratio`
- `congestion_proxy_percent`

### Definitions

- `segment_uncertainty`: a non-negative spread or uncertainty scalar describing
  confidence in the segment travel-time estimate
- `segment_reliability_score`: normalized score where higher means more stable
  and predictable segment behavior
- `congestion_proxy_ratio`: ratio of predicted or live segment travel time to a
  typical baseline segment time for the same segment/time bucket
- `congestion_proxy_percent`: readable slowdown percentage derived from the same
  proxy ratio

### Notes

- uncertainty may initially be residual-based rather than produced by a
  dedicated probabilistic model
- reliability may initially be derived from historical dispersion and live
  instability proxies rather than a separate classifier
- congestion proxy must be described as a slowdown proxy, not as literal city
  traffic density

## Route Scoring Input Contract V2

The routing layer must continue to use graph search, but the cost model will be
expanded in later phases.

### Current Routing Inputs

- predicted segment travel time
- wait before boarding
- fixed transfer buffer

### Locked Future Cost Factors

The generalized route cost model will be allowed to use:

- `travel_time_cost`
- `waiting_time_cost`
- `transfer_penalty_cost`
- `uncertainty_penalty_cost`
- `reliability_penalty_cost`
- `corridor_instability_penalty_cost`
- `detour_penalty_cost`
- optional `weather_penalty_cost`

### Route-Level Derived Outputs

The route service will eventually need to compute and expose:

- `total_predicted_eta_minutes`
- `total_wait_minutes`
- `total_in_vehicle_minutes`
- `route_reliability_score`
- `generalized_cost`
- `congestion_proxy_ratio`
- `congestion_proxy_percent`

## Explanation Contract

The backend will need to explain route selection explicitly. The route response
contract should reserve space for these factors:

- why the selected route beat competing options
- expected wait contribution
- reliability tradeoff
- transfer stability tradeoff
- slowdown or congestion-proxy tradeoff

The canonical explanation fields to support later are:

- `selection_reasons`
- `score_breakdown`
- `rejected_alternative_summaries`

### Expected Explanation Categories

- lower predicted journey time
- lower wait than alternatives
- lower fragility than alternatives
- lower slowdown than alternatives
- better reliability than alternatives

## Evaluation Output Contract

Evaluation artifacts must grow beyond point-regression metrics.

### Current Evaluation Outputs

- regression metrics for `actual_segment_minutes`
- regression metrics for `segment_delay_minutes`

### Locked Future Evaluation Outputs

- segment-level ETA error
- route-level ETA error
- waiting-time estimation error
- route recommendation comparison against baselines
- reliability improvement metrics
- congestion-proxy usefulness checks
- weather-ablation results if weather is enabled later

### Required Baseline Families

- static GTFS schedule routing
- historical-average segment routing
- current mean-ETA routing
- generalized-cost aligned routing

## File-By-File Implementation Map

This section locks where later phases should land.

### `api/training/config/default_config.toml`

Why it changes:

- this file defines the canonical training feature contract

Future changes:

- extend segment feature lists with live-state, road-context, congestion-proxy,
  and optional weather features
- preserve current target names and add metadata for uncertainty/reliability

### `api/training/data.py`

Why it changes:

- this is where raw data becomes the segment training frame

Future changes:

- enrich segment rows with road-context joins
- enrich segment rows with live operational proxy columns where historical data
  exists
- add baseline-time fields needed for congestion proxy computation

### `api/common/features.py`

Why it changes:

- this module prepares the final model frame used by training and inference

Future changes:

- support additional derived temporal or bucketed features
- support optional feature families without breaking current training

### `api/training/train_xgboost.py`

Why it changes:

- this is where training artifacts and metrics are defined

Future changes:

- emit schema metadata for v2 outputs
- record uncertainty/reliability-related metrics or calibration artifacts
- add ablation-friendly metrics for road-context, congestion proxy, and weather

### `api/app/services/gtfs_graph_service.py`

Why it changes:

- graph edges currently carry only transit schedule and distance metadata

Future changes:

- extend `SegmentEdge` to support road-context attributes and baseline-time
  metadata used by congestion proxy calculations

### `api/app/services/realtime_enrichment_service.py`

Why it changes:

- this is the correct home for GTFS-RT-derived live-state aggregates

Future changes:

- compute route, segment, stop, and corridor operational proxy metrics
- expose slowdown, bunching, headway, and instability signals for routing and
  prediction

### `api/app/services/prediction_service.py`

Why it changes:

- this service defines the inference output contract consumed by both the
  prediction API and routing service

Future changes:

- expand prediction payloads to include uncertainty, reliability, and
  congestion-proxy fields

### `api/app/services/route_optimization_service.py`

Why it changes:

- this service currently optimizes ETA plus wait only

Future changes:

- build richer segment records for prediction
- incorporate generalized route cost inputs
- emit route-level reliability, generalized cost, and explanation metadata

### `api/app/schemas/predictions.py`

Why it changes:

- schema contract must match the richer prediction output

Future changes:

- add optional or required fields for uncertainty, reliability, and congestion
  proxy outputs

### `api/app/schemas/routes.py`

Why it changes:

- route responses need to carry more than ETA and segment delay

Future changes:

- add fields for reliability, cost breakdown, congestion proxy, and
  explanations

### `api/app/api/v1/predictions.py`

Why it changes:

- API response models must stay aligned with prediction-service outputs

Future changes:

- no major behavior change expected beyond schema and response-shape updates

### `api/app/api/v1/routes.py`

Why it changes:

- route API will eventually expose generalized-cost and explanation data

Future changes:

- no major control-flow change expected beyond richer route response fields

### `api/tests/test_training_pipeline.py`

Why it changes:

- training contract changes must be pinned with tests

Future changes:

- assert v2 feature-frame behavior and optional feature-family compatibility

### `api/tests/test_prediction_api.py`

Why it changes:

- prediction output shape will expand

Future changes:

- assert uncertainty, reliability, and congestion-proxy output contract

### `api/tests/test_route_optimization_api.py`

Why it changes:

- route scoring and output contracts will expand materially

Future changes:

- assert generalized-cost behavior, transfer fragility behavior, and explanation
  fields

## Phase 1 Decisions Locked

Phase 1 locks these implementation decisions:

- `actual_segment_minutes` remains the primary target
- `predicted_segment_delay_minutes` remains a required derived output
- `segment_uncertainty` becomes a required future prediction output
- `segment_reliability_score` becomes a required future prediction output
- congestion is represented as a slowdown proxy, not literal traffic density
- weather remains optional and should be added only if it improves measurable
  results later
- the penalty system is formally treated as generalized route cost scoring,
  not reinforcement learning

## Immediate Next Step

Phase 2 should now design the road-context and optional weather-source contracts
that will feed the future feature pipeline without introducing paid or
unverifiable data dependencies.
