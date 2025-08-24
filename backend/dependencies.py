# utils/dependencies.py
from functools import lru_cache
from backend.models.prediction import PredictionModel
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[1] / "models/trained_model.pkl"
ENCODER_PATH = Path(__file__).resolve().parents[1] / "models/route_label_encoder.pkl"

@lru_cache()
def get_prediction_model():
    return PredictionModel(str(MODEL_PATH), str(ENCODER_PATH))
