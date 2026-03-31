from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib


@lru_cache(maxsize=1)
def load_model(model_path: str | Path):
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found at '{path}'.")
    return joblib.load(path)
