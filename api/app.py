from fastapi import FastAPI
from feast import FeatureStore

app = FastAPI()

# Initialisation du Feature Store (le repo est monté dans /repo)
store = FeatureStore(repo_path="/repo")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/features/{user_id}")
def get_features(user_id: str):
    features = [
        "subs_profile_fv:months_active",
        "subs_profile_fv:monthly_fee",
        "subs_profile_fv:paperless_billing",
    ]

    feature_dict = store.get_online_features(
        features=features,
        entity_rows=[{"user_id": user_id}],
    ).to_dict()

    # On convertit en format plus simple (clé -> valeur scalaires)
    simple = {name: values[0] for name, values in feature_dict.items()}

    return {
        "user_id": user_id,
        "features": simple,
    }

@app.get("/features/debug/all")
def debug_all_features():
    all_feature_views = store.list_feature_views()
    fv_names = [fv.name for fv in all_feature_views]
    return {"feature_views": fv_names}

@app.get("/features/debug/{feature_view_name}")
def debug_feature_view(feature_view_name: str):
    available_fvs = [fv.name for fv in store.list_feature_views()]
    if feature_view_name not in available_fvs:
        return {"error": f"Feature view not found. Available: {available_fvs}"}

    entity_df_sql = """
        SELECT user_id, '2024-01-31'::timestamp as event_timestamp
        FROM users
        LIMIT 50
    """

    try:
        fv = store.get_feature_view(feature_view_name)
        feature_names = [
            f"{feature_view_name}:{field.name}" 
            for field in fv.schema 
            if field.name != "user_id"
        ]

        df = store.get_historical_features(
            features=feature_names,
            entity_df=entity_df_sql,
        ).to_df()

        return {
            "feature_view": feature_view_name,
            "data": df.to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e)}