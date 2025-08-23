from __future__ import annotations
import os
import json
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth

app = FastAPI(
    title="Dynamic Route Rationalisation API",
    description="API backend for predicting bus delays and route rationalisation",
    version="1.0.0",
)

FRONTEND_ORIGINS: List[str] = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS if FRONTEND_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_firebase() -> None:
    if firebase_admin._apps:
        return
    
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    cred_file = os.getenv("FIREBASE_CREDENTIALS_FILE", "firebase-service-account.json")

    cred_obj = None
    if cred_json:
        try:
            cred_obj = credentials.Certificate(json.loads(cred_json))
        except Exception as e:
            raise RuntimeError(f"Invalid FIREBASE_CREDENTIALS_JSON: {e}")
    elif os.path.exists(cred_file):
        cred_obj = credentials.Certificate(cred_file)

    if cred_obj is None:
        raise RuntimeError(
            "Firebase credentials not found. "
            "Set FIREBASE_CREDENTIALS_JSON or place firebase-service-account.json "
            "(or set FIREBASE_CREDENTIALS_FILE)."
        )

    firebase_admin.initialize_app(cred_obj)

init_firebase()

bearer = HTTPBearer(auto_error=False)

def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
) -> Dict[str, Any]:
    if credentials is None or (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = credentials.credentials
    try:
        decoded = auth.verify_id_token(token)
        return decoded  
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

from routes.prediction import router as prediction_router
from routes.route_eta import router as route_eta_router

app.include_router(
    prediction_router,
    prefix="/api/predictions",
    tags=["Predictions"],
    dependencies=[Depends(verify_token)],
)

app.include_router(
    route_eta_router,
    prefix="/api/predictions",
    tags=["Predictions"],
    dependencies=[Depends(verify_token)],
)

@app.get("/ping")
def health_check():
    return {"status": "Backend is working"}

@app.get("/protected")
def protected(user: Dict[str, Any] = Depends(verify_token)):
    return {"message": "Hello from protected route!", "uid": user.get("uid")}
