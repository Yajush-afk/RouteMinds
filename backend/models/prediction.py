import joblib
from pathlib import Path
import numpy as np
from ..config import MODEL_PATH, METADATA_PATH, ENCODER_PATH

class PredictionModel:
    def __init__(self, model_path: Path = MODEL_PATH, metadata_path: Path = METADATA_PATH):
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self._model = None
        self._metadata = None
        self._load()

    def _load(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        self._model = joblib.load(self.model_path)
        try:
            self._metadata = joblib.load(self.metadata_path)
        except Exception:
            #fallback to JSON read
            import json
            if self.metadata_path.exists():
                with open(self.metadata_path, "r") as f:
                    self._metadata = json.load(f)
            else:
                self._metadata = {}

    @property
    def model(self):
        return self._model

    @property
    def metadata(self):
        return self._metadata

    def predict(self, X: np.ndarray):
        if self._model is None:
            raise RuntimeError("Model not loaded")
        preds = self._model.predict(X)
        return np.array(preds).astype(float)