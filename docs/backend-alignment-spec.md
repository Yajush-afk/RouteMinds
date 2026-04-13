# Backend Alignment Spec

## Purpose

This document locks the scope and design constraints for the `backend/alignment`
branch so that implementation work stays aligned with the RouteMinds problem
statement:

> "Dynamic route rationalization model based on machine learning/AI would be
> required based on real-time traffic and road parameters."

This is a branch-level implementation spec for backend work only. Frontend
integration and route drawing are intentionally out of scope for this phase and
will follow after the backend alignment phases are complete.

## Current Architecture To Preserve

RouteMinds already has a solid backend foundation. The alignment work must
extend this foundation instead of replacing it.

The current architecture to preserve is:

- `api/training/*`: offline feature engineering and model training
- `api/app/services/gtfs_graph_service.py`: GTFS static graph construction and
  stop/edge metadata
- `api/app/services/realtime_enrichment_service.py`: GTFS-RT ingestion and live
  operational enrichment
- `api/app/services/prediction_service.py`: model inference contract
- `api/app/services/route_optimization_service.py`: graph-based route search and
  scoring
- `api/app/api/v1/*`: API surface for predictions, stops, routes, and real-time

## Design Principles

The `backend/alignment` branch must follow these rules:

- RouteMinds remains a prediction-driven transit routing engine.
- Machine learning predicts segment-level transit behavior; it does not replace
  graph routing.
- Graph search remains interpretable and auditable.
- Road-awareness must come from zero-cost data sources and derived proxies.
- Real-time behavior should be modeled through GTFS-RT operational signals and
  not through paid traffic APIs.
- System-level intelligence should remain lightweight and should only support
  better passenger route recommendation.
- The backend must expose explainable route recommendations rather than a
  black-box "AI chose this path" result.

## Product Interpretation

For backend alignment purposes, RouteMinds is defined as:

- a real-time ML-assisted passenger route recommendation engine
- built on GTFS network data, predictive segment travel-time modeling, live
  transit updates, and road-aware dynamic routing

RouteMinds is not defined as:

- a citywide autonomous traffic optimization platform
- a bus network redesign engine
- a general road navigation system for private vehicles
- an end-to-end opaque AI route selector

## Scope

The backend alignment work is in scope for:

- explicit road-context feature integration
- uncertainty and reliability modeling for segment predictions
- waiting-time and boarding-feasibility modeling
- route reranking using multiple interpretable factors
- realistic transfer-awareness and transfer fragility penalties
- lightweight route- and corridor-level service quality indicators
- baseline evaluation against simpler routing alternatives
- API outputs that explain why a route was chosen

## Non-Goals

The backend alignment work is out of scope for:

- full citywide traffic signal control or road network optimization
- multimodal trip planning beyond the current transit-routing problem framing
- paid traffic APIs or closed commercial data feeds
- end-to-end deep learning route selection that bypasses graph optimization
- a separate operations dashboard product
- frontend map rendering, route drawing, or UI wiring in this branch phase

## Data Source Contract

Allowed primary data sources for `backend/alignment` are:

- GTFS static data already present in the project
- GTFS-RT vehicle-position data already integrated in the backend
- OpenStreetMap-derived static road context
- optional free weather data in later phases if it improves measurable routing
  quality

The branch must assume a zero-budget constraint. Any proposed feature that
depends on paid APIs or unavailable proprietary feeds is out of scope.

## Meaning Of "Road Parameters"

To keep the problem-statement alignment precise, "road parameters" in RouteMinds
means the following categories:

- OSM-derived road context such as road hierarchy, junction complexity,
  intersection density, and corridor tags
- GTFS-RT-derived congestion proxies such as rolling slowdown, bunching,
  headway irregularity, and delay propagation
- optional free weather-conditioned slowdown features in later phases

This branch should not claim access to direct citywide live road traffic feeds
unless such a free source is actually integrated and tested.

## Prediction Contract

### Primary Prediction Target

The primary ML target remains:

- `actual_segment_minutes`

This preserves continuity with the current model architecture and keeps the
prediction target directly useful for graph edge scoring.

### Secondary Outputs

The aligned backend should expand prediction outputs to include:

- `predicted_segment_delay_minutes`
- `segment_uncertainty`
- `segment_reliability_score`

These outputs may initially be derived from residual distributions or quantile
approximations and may later be upgraded to more formal quantile models.

### Feature Families

The aligned model pipeline is expected to support these feature families:

- transit operation features
- temporal features
- recent live-delay and slowdown context
- headway and waiting-related proxies where available
- road-context metadata
- corridor-specific congestion tendencies
- optional weather features in later phases

## Routing Contract

Route optimization must remain graph-based and interpretable.

Machine learning will provide dynamic segment estimates and reliability-related
signals. The routing layer will continue to choose paths using explicit scoring
rules over graph edges and transfers.

The route-selection logic must evolve from ETA-only ranking to a multi-factor
ranking model that can combine:

- predicted travel time
- expected waiting time
- transfer penalties
- uncertainty and reliability penalties
- unsafe or unstable corridor penalties where supported by free data
- detour penalties where necessary

The route scorer must remain inspectable so the backend can explain why a route
was chosen.

## Explainability Contract

The aligned backend should be able to explain route recommendations using clear
factors such as:

- lower total predicted journey time
- lower expected waiting time
- lower transfer fragility
- better corridor reliability at the query time
- lower live slowdown than competing options

The explanation layer is a required backend capability because frontend wiring
and judging both depend on it later.

## Evaluation Contract

The aligned backend must demonstrate measurable value against simpler baselines.

Required baseline families are:

- static GTFS schedule-based routing
- shortest-distance or default graph routing where applicable
- historical-average segment-time routing if supported by the data
- current ML mean-ETA routing
- aligned reliability-aware routing

Required evaluation categories are:

- ETA prediction error
- route recommendation quality
- waiting-time realism
- reliability improvement
- passenger travel-time reduction
- performance during peak and disruption-heavy periods

## Implementation Boundaries

To prevent branch drift, the following boundaries are locked now:

- ML remains focused on prediction, uncertainty, and reliability.
- Graph search remains the path-selection mechanism.
- Road-awareness must be explicit in the feature pipeline and route scorer.
- System-level intelligence must stay lightweight and route-supportive.
- Any new feature must improve at least one of:
  - prediction quality
  - recommendation quality
  - reliability estimation
  - explainability

If a proposed feature does not improve one of those categories, it should be
treated as scope creep.

## Phase Structure

Phase 0 is this alignment spec. The remaining backend implementation phases are:

1. Data and contract audit
2. Road-context and external-context design
3. Realtime operational proxy enrichment
4. Waiting-time and boarding modeling
5. Reliability and uncertainty modeling
6. Segment prediction pipeline v2
7. Generalized route cost scoring
8. Transfer-awareness and fragility
9. Lightweight system-level intelligence
10. Evaluation framework and baselines
11. API and explanation layer
12. Test expansion
13. Documentation and competition packaging

Frontend integration and route drawing are intentionally deferred until these
backend phases are complete.

## Acceptance Criteria For Backend Alignment

The `backend/alignment` branch is considered complete only when all of the
following are true:

- the backend still uses GTFS graph routing rather than black-box path selection
- segment predictions include travel time plus reliability-related output
- route scoring is no longer ETA-only
- waiting time is explicitly modeled as part of journey ETA
- route recommendations handle transfer fragility more realistically
- at least one explicit road-context input source is integrated into the backend
- GTFS-RT-derived congestion or instability proxies affect route scoring
- evaluation artifacts compare the aligned system against simpler baselines
- route responses can explain why a route was selected
- documentation and implementation claims remain consistent with the actual
  data sources and capabilities

## Immediate Next Step

Phase 1 should now audit and formalize the exact feature, schema, and service
contracts that need to change to satisfy this spec without breaking the core
backend architecture.
