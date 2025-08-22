from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from ..schemas.prediction import DelayRequest, DelayResponse
from ..dependencies import get_prediction_model
from ..utils.preprocessing import build_feature_vector
from sklearn.exceptions import NotFittedError

router = APIRouter(tags=["predictions"])

@router.post("/predict_delay", response_model=DelayResponse)
def predict_delay(request: DelayRequest, pm = Depends(get_prediction_model)):
    """
    Predict delay in minutes for a single stop event.
    """
    # Convert request to dict
    req = request.model_dump()
    try:
        X = build_feature_vector(req)   # shape (1, n_features)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preprocessing error: {e}")

    try:
        preds = pm.predict(X)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model prediction error: {e}")

    return DelayResponse(predicted_delay=float(preds[0]), model=pm.metadata.get("model_type"))
