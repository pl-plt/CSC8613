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


# TODO 2: Mettre une requête POST
@app.post("/predict")
def predict(payload: UserPayload):
    if store is None or model is None:
        return {"error": "Model or feature store not initialized"}

    # TODO (optionel) à adapter si besoin
    features_request = [
            "subs_profile_fv:months_active",
            "subs_profile_fv:monthly_fee",
            "subs_profile_fv:paperless_billing",
            "subs_profile_fv:plan_stream_tv",
            "subs_profile_fv:plan_stream_movies",
            "subs_profile_fv:net_service",
            "usage_agg_30d_fv:watch_hours_30d",
            "usage_agg_30d_fv:avg_session_mins_7d",
            "usage_agg_30d_fv:unique_devices_30d",
            "usage_agg_30d_fv:skips_7d",
            "usage_agg_30d_fv:rebuffer_events_7d",
            "payments_agg_90d_fv:failed_payments_90d",
            "support_agg_90d_fv:support_tickets_90d",
            "support_agg_90d_fv:ticket_avg_resolution_hrs_90d",
        ]


    # TODO 3 : Récupérer les features online
    feature_dict = store.get_online_features(
            features=features_request,
            entity_rows=[{"user_id": payload.user_id}],
        ).to_dict()

    X = pd.DataFrame({k: [v[0]] for k, v in feature_dict.items()})

    # Gestion des features manquantes
    if X.isnull().any().any():
            missing = X.columns[X.isnull().any()].tolist()
            return {
                "error": f"Missing features for user_id={payload.user_id}",
                "missing_features": missing,
            }

    # Nettoyage minimal (évite bugs de types)
    X = X.drop(columns=["user_id"], errors="ignore")

    # TODO 4: appeler le modèle et produire la réponse JSON (prediction + proba optionnelle)
    # Astuce : la plupart des modèles MLflow “pyfunc” utilisent model.predict(X)
    # (on ne suppose pas predict_proba ici)
    y_pred = model.predict(X)

    # TODO 5 : Retourner la prédiction
    return {
        "user_id": payload.user_id,
        "prediction": int(y_pred[0]),
        "features_used": X.to_dict(orient="records")[0],
    }