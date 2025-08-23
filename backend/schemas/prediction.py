from pydantic import BaseModel


class PredictionRequest(BaseModel):
    route_id: str
    feature1: float
    feature2: float
    feature3: float
    #add as many numerical features as your model expects


class PredictionResponse(BaseModel):
    route_id: str
    prediction: float
