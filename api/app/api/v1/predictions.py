from fastapi import APIRouter

from api.app.core.config import settings
from api.app.schemas.predictions import (
    SegmentPredictionRequest,
    SegmentPredictionResponse,
)
from api.app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def get_prediction_service() -> PredictionService:
    return PredictionService(
        model_path=settings.MODEL_PATH,
        schema_path=settings.SCHEMA_PATH,
        v2_manifest_path=settings.MODEL_V2_MANIFEST_PATH or None,
    )


@router.post("/segments", response_model=SegmentPredictionResponse)
async def predict_segments(
    request: SegmentPredictionRequest,
) -> SegmentPredictionResponse:
    prediction_service = get_prediction_service()
    predictions = prediction_service.predict_segments(
        [segment.model_dump() for segment in request.segments]
    )
    return SegmentPredictionResponse(predictions=predictions)
