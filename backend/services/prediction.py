from models.prediction import PredictionModel
from schemas.prediction import PredictionRequest, PredictionResponse


class PredictionService:
    def __init__(self, model_path: str, encoder_path: str):
        self.model = PredictionModel(model_path, encoder_path)

    def make_prediction(self, request: PredictionRequest) -> PredictionResponse:
        features = [request.feature1, request.feature2, request.feature3]
        prediction = self.model.predict(request.route_id, features)

        return PredictionResponse(
            route_id=request.route_id,
            prediction=prediction
        )
