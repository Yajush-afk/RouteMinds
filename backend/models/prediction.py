import joblib
from pathlib import Path
import numpy as np


class PredictionModel:
    def __init__(self, model_path: str, encoder_path: str):
        base_path = Path(__file__).parent
        self.model = joblib.load(base_path / model_path)
        self.encoder = joblib.load(base_path / encoder_path)

    def encode_route(self, route_id: str) -> int:
        """Convert route_id string into encoded integer"""
        if route_id not in self.encoder.classes_:
            raise ValueError(f"Route ID '{route_id}' not found in encoder classes.")
        return int(self.encoder.transform([route_id])[0])

    def predict(self, route_id: str, features: list[float]) -> float:
        """Make a single prediction"""
        encoded_route = self.encode_route(route_id)
        X = np.array([encoded_route] + features).reshape(1, -1)
        return float(self.model.predict(X)[0])
