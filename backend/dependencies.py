from functools import lru_cache
from .models.prediction import PredictionModel

@lru_cache()
def get_prediction_model():
    return PredictionModel()