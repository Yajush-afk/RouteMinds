from fastapi import APIRouter

router = APIRouter(prefix="/routes", tags=["Routes"])

@router.get("/")
async def list_routes():
    return {"message": "Route endpoints coming soon"}