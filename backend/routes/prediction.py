from fastapi import APIRouter, Depends, HTTPException
from schemas.prediction import PredictionRequest, PredictionResponse
from services.prediction import PredictionService
from services.eta import ETAService
from schemas.route_eta import RouteEtaRequest, RouteEtaResponse

router = APIRouter()

# ML model service (keep your existing paths)
prediction_service = PredictionService(
    model_path="backend/models/trained_model.pkl",
    encoder_path="backend/models/route_label_encoder.pkl"
)

# ETA service — make sure this path points to your full dataset
eta_service = ETAService(
    dataset_path="data/processed/bus_delay_dataset.csv"
)


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    """
    ML model prediction (using trained_model.pkl).
    """
    try:
        return prediction_service.make_prediction(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/predict_delay", response_model=RouteEtaResponse)
def predict_delay(request: RouteEtaRequest):
    """
    Dataset-backed ETA prediction (uses historical averages from bus_delay_dataset.csv).
    Returns a RouteEtaResponse containing waypoints, per-stop predictions, and a summary.
    """
    if eta_service is None:
        raise HTTPException(status_code=503, detail="ETA service not initialized on server")

    try:
        return eta_service.get_eta(request)
    except ValueError as e:
        # Bad input / missing data
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        # dataset or other file missing
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # unexpected
        raise HTTPException(status_code=500, detail="Internal server error")
