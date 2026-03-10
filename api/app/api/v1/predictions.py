from fastapi import APIRouter

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("/")
async def get_predictions():
    return {"message": "Prediction endpoints coming in Phase 4"}