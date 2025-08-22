from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = (BASE_DIR / "models").resolve()

MODEL_PATH = MODELS_DIR / "trained_model.pkl"
ENCODER_PATH = MODELS_DIR / "route_label_encoder.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

# If you keep models one level up (you mentioned backend/models/), adjust accordingly.
# The above assumes config.py is in backend/ and models/ sibling to this file.
