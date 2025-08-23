from fastapi import APIRouter, Depends, HTTPException
from schemas.prediction import PredictionRequest, PredictionResponse
from services.prediction import PredictionService

router = APIRouter()

# Load service once at startup
prediction_service = PredictionService(
    model_path="artifacts/trained_model.pkl",
    encoder_path="artifacts/encoder.pkl"
)


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        return prediction_service.make_prediction(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
