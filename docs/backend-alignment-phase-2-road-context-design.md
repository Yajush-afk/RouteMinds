# Backend Alignment Phase 2: Road-Context And External Context Design

## Purpose

Phase 2 makes "road parameters" explicit in the RouteMinds backend design.
This phase defines the zero-cost external context contract that later phases will
use for feature engineering, live-state scoring, and route explanation.

This phase still does not change model behavior. It locks the road-aware and
weather-aware design before implementation work begins in the training and
service layers.

## Scope

This phase covers:

- OSM-derived static road context
- optional weather-source contract
- corridor tags and risk metadata
- congestion-proxy definition
- feature naming and ownership boundaries

This phase does not include:

- direct ingestion of paid traffic APIs
- use of the 2020 Delhi traffic-density dataset
- runtime model changes
- routing-cost implementation

## Design Goals

The external context design must satisfy these constraints:

- zero-budget compatible
- explainable to judges and users
- segment-level joinability with GTFS-derived edges
- useful both for offline training and online scoring
- robust enough to degrade gracefully when optional context is unavailable

## Data Source Contract

### Required Road-Context Source

The required static road-context source is OpenStreetMap-derived metadata.

The backend should treat OSM-derived metadata as:

- a static context layer
- segment-aligned or corridor-aligned road information
- a source of road-structure signals, not direct live traffic measurements

### Optional Weather Source

Weather is an optional external source. It should only be integrated if it can
be added with a free API and if later evaluation shows measurable improvement.

The recommended weather-source contract is:

- hourly or sub-hourly historical and forecast weather
- city-level or grid-level weather that can be joined by timestamp
- features focused on rainfall and temperature first

Recommended candidate source class:

- free weather APIs such as Open-Meteo or an equivalent no-cost provider

### Explicitly Excluded Sources

The following sources are out of scope for the alignment branch:

- paid traffic feeds
- proprietary map APIs for road-speed data
- 2020 Delhi traffic-density camera dataset as a main modeling input
- unverifiable social or incident feeds unless separately approved later

## Road-Context Model

Road context should be represented as metadata attached to GTFS segment edges or
to segment-level training rows derived from those edges.

The first version should use corridor-level or segment-level approximation. Full
high-precision map matching is not required for the initial aligned backend.

### Required Road-Context Fields

The following fields are approved for the initial road-context contract:

- `road_hierarchy`
- `intersection_density`
- `junction_complexity_score`
- `signal_density_proxy`
- `corridor_risk_tag`
- `corridor_tag`

### Field Definitions

#### `road_hierarchy`

Normalized category describing the dominant road class associated with a GTFS
segment or corridor.

Expected values should be low-cardinality, such as:

- `motorway_like`
- `arterial`
- `collector`
- `local`
- `mixed`
- `unknown`

This field is intended to capture coarse movement characteristics rather than
raw OSM tag complexity.

#### `intersection_density`

Numeric proxy for how intersection-heavy a segment or corridor is.

Interpretation:

- low values indicate smoother uninterrupted movement potential
- high values indicate more stop-go complexity and signal interaction

This should be normalized to a consistent unit such as intersections per km.

#### `junction_complexity_score`

Numeric proxy for the complexity of nearby intersections or merges.

Interpretation:

- low values represent simpler geometry and likely fewer conflict points
- high values represent more complex junction behavior and potentially greater
  variability

This score can be heuristic at first.

#### `signal_density_proxy`

Numeric proxy describing the density of signalized interruption along or near the
segment.

Interpretation:

- low values suggest fewer signal-related stops
- high values suggest greater stop-go risk

#### `corridor_risk_tag`

Low-cardinality categorical tag used to represent corridor-level instability or
risk characteristics.

Expected values may include:

- `stable`
- `moderate_risk`
- `high_risk`
- `unknown`

This should remain conservative and explainable.

#### `corridor_tag`

General descriptive tag for a segment group or movement pattern.

Examples may include:

- `junction_heavy`
- `arterial_mixed_flow`
- `dense_core`
- `peripheral_stretch`
- `unknown`

This is intended primarily for feature engineering and explanation support.

## Optional Weather Feature Contract

Weather remains optional. If added later, the first version should use a minimal
schema.

### Approved Weather Fields

- `weather_rainfall_mm`
- `weather_temperature_c`
- `weather_is_adverse`

### Weather Design Principles

- rainfall is the highest-priority weather feature
- weather should join on timestamp, not on ad hoc manual labels
- weather features must be optional at inference time
- if weather is missing, the backend must still operate normally

### Weather Interpretation

- `weather_rainfall_mm`: continuous precipitation intensity feature
- `weather_temperature_c`: ambient temperature feature for extreme heat effects
- `weather_is_adverse`: compact boolean or binary flag for high-friction weather

Humidity, visibility, or wind should only be added if later evaluation supports
their value.

## Congestion Proxy Contract

RouteMinds should not claim direct citywide traffic density measurement. Instead,
the backend will use a slowdown-based congestion proxy.

### Canonical Definition

The canonical congestion proxy ratio is:

`predicted_or_live_segment_time / typical_segment_time`

Where:

- `predicted_or_live_segment_time` is the segment travel time from model output
  or live operational estimate
- `typical_segment_time` is a baseline expectation for the same segment under a
  comparable time bucket

### Approved Derived Fields

- `congestion_proxy_ratio`
- `congestion_proxy_percent`

### Definitions

#### `congestion_proxy_ratio`

Primary numeric slowdown ratio.

Interpretation:

- `1.0` means typical conditions
- `> 1.0` means slower-than-typical conditions
- `< 1.0` means faster-than-typical conditions

#### `congestion_proxy_percent`

Readable slowdown percentage derived from the ratio.

Recommended formula:

`((congestion_proxy_ratio - 1.0) * 100.0)`

Interpretation example:

- ratio `1.50` becomes `50%` slower than typical

### Baseline Definition

The baseline `typical_segment_time` should be defined using a deterministic,
historical time-bucket baseline for the same segment, such as:

- same route-stop pair
- same hour-of-day bucket
- same weekday/weekend bucket

This baseline must be stable, explainable, and derivable from RouteMinds-owned
data artifacts.

## Ownership And Join Strategy

### GTFS Graph Ownership

The GTFS graph layer will own static segment metadata that is stable over time,
including:

- distance-based attributes
- schedule-based attributes
- static road-context attributes
- static baseline metadata keys

### Realtime Enrichment Ownership

The GTFS-RT enrichment layer will own live dynamic context, including:

- live delay state
- slowdown ratios
- bunching and headway irregularity
- live corridor instability indicators

### Training Pipeline Ownership

The training pipeline will own offline joins and derived model features,
including:

- baseline time-bucket features
- road-context features
- optional weather joins
- historical slowdown features

### Prediction Service Ownership

The prediction service will own the final inference output shape, including:

- predicted segment time
- delay output
- uncertainty output
- reliability output
- congestion-proxy fields

## Segment Metadata Design Direction

Later implementation phases should extend segment-level graph metadata in a way
that keeps static and dynamic signals separate.

Static edge metadata should eventually support:

- route and stop identifiers
- segment geometry surrogates such as distance and progress
- road-context fields
- baseline segment-time lookup keys

Dynamic context should be fetched or computed separately and should not be baked
directly into static graph artifacts.

## Graceful Degradation Rules

The external-context design must degrade gracefully.

### If OSM Road Context Is Missing

The backend should:

- preserve routing functionality
- use neutral defaults such as `unknown` categories or zeroed numeric proxies
- avoid failing prediction or route optimization outright

### If Weather Context Is Missing

The backend should:

- preserve full routing and prediction functionality
- skip optional weather features
- avoid failing requests due to absent weather data

### If Live Context Is Missing

The backend should:

- fall back to static baseline and model predictions
- compute congestion proxy from predicted time vs historical baseline where
  possible

## File-By-File Impact Map For Later Phases

### `api/app/services/gtfs_graph_service.py`

Later work will need to:

- extend `SegmentEdge` with road-context metadata fields
- add baseline-lookup metadata needed for congestion proxy support

### `api/training/data.py`

Later work will need to:

- join segment rows with road-context data
- support baseline segment-time derivation for congestion proxy features
- support optional weather joins

### `api/training/config/default_config.toml`

Later work will need to:

- declare approved road-context features
- declare optional weather features
- declare baseline-related fields used for congestion proxy logic

### `api/app/services/realtime_enrichment_service.py`

Later work will need to:

- compute live slowdown or instability signals that feed congestion-proxy logic

### `api/app/services/prediction_service.py`

Later work will need to:

- expose congestion-proxy output fields alongside travel-time predictions

### `api/app/services/route_optimization_service.py`

Later work will need to:

- consume congestion-proxy fields and road-aware metadata when generalized route
  cost scoring is implemented

## Decisions Locked In Phase 2

Phase 2 locks these decisions:

- road awareness will come from OSM-derived static road context plus GTFS-RT
  dynamic operational proxies
- weather is allowed but optional
- the 2020 Delhi traffic-density dataset is excluded from the aligned backend
  design
- congestion is represented as a slowdown proxy relative to a typical baseline
- road-context features should remain low-cardinality and explainable in the
  first implementation
- the initial road-context implementation does not require full high-precision
  map matching

## Immediate Next Step

Phase 3 should now implement the live operational proxy layer that produces
segment, stop, route, and corridor instability signals from GTFS-RT data.
