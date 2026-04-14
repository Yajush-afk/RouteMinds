# Backend Alignment Competition Summary

## Positioning

RouteMinds is a prediction-driven transit routing backend for Delhi that replaces
static timetable assumptions with live, risk-aware route selection.

The backend aligns to the problem statement by combining:

- machine-learning-based segment travel-time prediction
- GTFS graph routing over dynamic edge costs
- GTFS-RT-derived live operational proxies
- slowdown-based congestion proxies rather than unsupported direct traffic density
- explainable generalized route cost scoring

## Implemented Prototype Capabilities

- segment travel-time prediction with delay, uncertainty, and reliability outputs
- GTFS graph routing over predicted segment costs
- live GTFS-RT enrichment for route delay, corridor slowdown, bunching, and
  headway irregularity
- wait-aware ETA modeling and boarding-feasibility scoring
- transfer fragility, missed-transfer risk, and fragile-transfer penalties
- generalized route cost scoring with interpretable penalty components
- service-quality and corridor-instability indicators
- route-response explanations, risk fields, and congestion-proxy outputs
- baseline evaluation framework for static schedule, historical average, and ML
  ETA baselines

## Precision Notes

When presenting the system, use the following precise claims:

- say `slowdown-based congestion proxy` instead of `live traffic density percentage`
- say `road-aware dynamic routing architecture` instead of claiming full direct
  road-sensor coverage
- say `GTFS-RT operational proxies` for live traffic-sensitive context
- say `prediction-driven route recommendation` rather than black-box AI route
  selection

## Judge-Facing Value

The backend prototype now demonstrates that RouteMinds can:

- recommend routes using more than static schedules
- account for waiting time, instability, and fragile transfers
- expose why a route was chosen
- compare ML-assisted ETA behavior against simpler baselines

This is enough for a strong prototype demo while keeping the heavier real-data
model retraining work as a later-round enhancement.
