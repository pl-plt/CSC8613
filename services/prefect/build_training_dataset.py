import os
import pandas as pd
from sqlalchemy import create_engine
from feast import FeatureStore

AS_OF = "2024-01-31"
FEAST_REPO = "/repo"

def get_engine():
    uri = (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER','streamflow')}:"
        f"{os.getenv('POSTGRES_PASSWORD','streamflow')}@"
        f"{os.getenv('POSTGRES_HOST','postgres')}:5432/"
        f"{os.getenv('POSTGRES_DB','streamflow')}"
    )
    return create_engine(uri)

def build_entity_df(engine, as_of: str) -> pd.DataFrame:
    q = """
    SELECT user_id, as_of
    FROM subscriptions_profile_snapshots
    WHERE as_of = %(as_of)s
    """
    df = pd.read_sql(q, engine, params={"as_of": as_of})
    if df.empty:
        raise RuntimeError(f"No snapshot rows found at as_of={as_of}")
    df = df.rename(columns={"as_of": "event_timestamp"})
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
    return df[["user_id", "event_timestamp"]]

def fetch_labels(engine, as_of: str) -> pd.DataFrame:
    # Version simple : table labels(user_id, churn_label)
    q = "SELECT user_id, churn_label FROM labels"
    labels = pd.read_sql(q, engine)
    if labels.empty:
        raise RuntimeError("Labels table is empty.")
    labels["event_timestamp"] = pd.to_datetime(as_of)
    return labels[["user_id", "event_timestamp", "churn_label"]]

def main():
    engine = get_engine()
    entity_df = build_entity_df(engine, AS_OF)
    labels = fetch_labels(engine, AS_OF)

    store = FeatureStore(repo_path=FEAST_REPO)

    # TODO: définir la liste de features à récupérer
    features = [
        "subs_profile_fv:months_active",
        "subs_profile_fv:monthly_fee",
        "subs_profile_fv:paperless_billing",
        "usage_agg_30d_fv:watch_hours_30d",
        "usage_agg_30d_fv:avg_session_mins_7d",
        "payments_agg_90d_fv:failed_payments_90d",
        

    ]

    hf = store.get_historical_features(
        entity_df=entity_df,
        features=features,
    ).to_df()

    df = hf.merge(labels, on=["user_id", "event_timestamp"], how="inner")

    if df.empty:
        raise RuntimeError("Training set is empty after merge. Check AS_OF and labels.")

    os.makedirs("/data/processed", exist_ok=True)
    df.to_csv("/data/processed/training_df.csv", index=False)
    print(f"[OK] Wrote /data/processed/training_df.csv with {len(df)} rows")

if __name__ == "__main__":
    main()