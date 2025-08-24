from fastapi import APIRouter, HTTPException
from ..schemas.route_eta import RouteEtaRequest, RouteEtaResponse
from ..services.ai_routing import ai_routing_service  # Make sure this exists and is initialized

router = APIRouter()

@router.post("/route_eta", response_model=RouteEtaResponse)
def route_eta_endpoint(req: RouteEtaRequest):
    """
    Computes ETA for a route using AI routing service.
    """
    try:
        resp = ai_routing_service.compute_route_eta(req)
        return resp
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
