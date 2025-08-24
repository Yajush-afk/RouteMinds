from ..models.prediction import PredictionModel
from ..schemas.prediction import PredictionRequest, PredictionResponse
from pathlib import Path


class PredictionService:
    def __init__(self, model_path: str = "models/trained_model.pkl", encoder_path: str = "models/route_label_encoder.pkl"):
        base_path = Path(__file__).parent.parent  # backend/
        self.model = PredictionModel(
            model_path=base_path / model_path,
            encoder_path=base_path / encoder_path
        )

    def make_prediction(self, request: PredictionRequest) -> PredictionResponse:
        features = [request.feature1, request.feature2, request.feature3]
        prediction = self.model.predict(request.route_id, features)

        return PredictionResponse(
            route_id=request.route_id,
            prediction=prediction
        )
