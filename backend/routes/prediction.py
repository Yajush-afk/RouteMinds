from fastapi import APIRouter, HTTPException
from ..schemas.prediction import PredictionRequest, PredictionResponse
from ..services.prediction import PredictionService
from ..services.eta import ETAService
from ..schemas.route_eta import RouteEtaRequest, RouteEtaResponse
from pathlib import Path

router = APIRouter()

# ML model service
prediction_service = PredictionService(
    model_path="models/trained_model.pkl",
    encoder_path="models/route_label_encoder.pkl"
)

# ETA service — full path
eta_service = ETAService(
    dataset_path=Path(__file__).parent.parent / "../data/processed/bus_delay_dataset.csv"
)


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        return prediction_service.make_prediction(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/predict_delay", response_model=RouteEtaResponse)
def predict_delay(request: RouteEtaRequest):
    if eta_service is None:
        raise HTTPException(status_code=503, detail="ETA service not initialized")

    try:
        return eta_service.get_eta(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
