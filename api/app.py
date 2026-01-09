from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from fastapi import FastAPI
from pydantic import BaseModel
from feast import FeatureStore

app = FastAPI(title="StreamFlow Churn Prediction API")

# Initialisation du Feature Store (le repo est monté dans /repo)
store = FeatureStore(repo_path="/repo")

import mlflow.pyfunc
import pandas as pd
import os


# --- Config ---
REPO_PATH = "/repo"
# TODO 1: complétez avec le nom de votre modèle
MODEL_URI = "models:/streamflow_churn/Production"

try:
    store = FeatureStore(repo_path=REPO_PATH)
    model = mlflow.pyfunc.load_model(MODEL_URI)
except Exception as e:
    print(f"Warning: init failed: {e}")
    store = None
    model = None


class UserPayload(BaseModel):
    user_id: str


@app.get("/health")
def health():
    return {"status": "ok"}

REQUEST_COUNT = Counter("api_requests_total", "Total number of API requests")
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Latency of API requests in seconds")


@app.post("/predict")
def predict(payload: UserPayload):
    start_time = time.time()

    REQUEST_COUNT.inc()

    # Logique devant normalement exister dans votre code
    if store is None or model is None:
        return {"error": "Model or feature store not initialized"}

    features_request = [
        "subs_profile_fv:paperless_billing",
        "subs_profile_fv:plan_stream_tv",
        "subs_profile_fv:plan_stream_movies",
    ]

    X = X.drop(columns=["user_id"], errors="ignore")
    y_pred = model.predict(X)[0]

    REQUEST_LATENCY.observe(time.time() - start_time)

    return {
        "user_id": payload.user_id,
        "prediction": int(y_pred),
        "features_used": X.to_dict(orient="records")[0],
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)