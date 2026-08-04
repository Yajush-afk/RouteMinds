from __future__ import annotations

from importlib import import_module

_SERVICE_MODULES = {
    "GTFSGraphService": "api.app.services.gtfs_graph_service",
    "GTFSRealtimeIngestionService": "api.app.services.realtime_enrichment_service",
    "PredictionService": "api.app.services.prediction_service",
    "RealtimeEnrichmentService": "api.app.services.realtime_enrichment_service",
    "RouteOptimizationService": "api.app.services.route_optimization_service",
}

__all__ = list(_SERVICE_MODULES)


def __getattr__(name: str):
    module_name = _SERVICE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
