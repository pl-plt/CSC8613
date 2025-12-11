import os
import pandas as pd
from sqlalchemy import create_engine, text
from prefect import flow, task

# Configuration de la base PostgreSQL (via .env)
PG = {
    "user": os.getenv("POSTGRES_USER", "streamflow"),
    "pwd":  os.getenv("POSTGRES_PASSWORD", "streamflow"),
    "db":   os.getenv("POSTGRES_DB", "streamflow"),
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

# Valeurs par défaut pour ce TP (vous pouvez les surcharger avec des variables d'environnement)
AS_OF = os.getenv("AS_OF", "2024-01-31")               # frontière du mois
SEED_DIR = os.getenv("SEED_DIR", "/data/seeds/month_000")


def engine():
    """Crée un engine SQLAlchemy pour PostgreSQL."""
    uri = f"postgresql+psycopg2://{PG['user']}:{PG['pwd']}@{PG['host']}:{PG['port']}/{PG['db']}"
    return create_engine(uri)


@task
def upsert_csv(table: str, csv_path: str, pk_cols: list[str]):
    """
    Charge un CSV dans une table Postgres en utilisant une stratégie d'upsert.
    1) Création d'une table temporaire
    2) Insert dans la table temporaire
    3) INSERT ... SELECT ... FROM temp ON CONFLICT (...) DO UPDATE ...
    """
    df = pd.read_csv(csv_path)

    # Conversion de certains types si nécessaire (ex: dates, booléens)
    if "signup_date" in df.columns:
        df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")

    # TODO: convertir en booléen les colonnes plan_stream_tv, plan_stream_movies, paperless_billing si elles existent
    # À compléter pour les colonnes pertinentes.
    if "plan_stream_tv" in df.columns:
        df["plan_stream_tv"] = df["plan_stream_tv"].astype(bool)
    if "plan_stream_movies" in df.columns:
        df["plan_stream_movies"] = df["plan_stream_movies"].astype(bool)
    if "paperless_billing" in df.columns:
        df["paperless_billing"] = df["paperless_billing"].astype(bool)

    eng = engine()
    with eng.begin() as conn:
        tmp = f"tmp_{table}"

        # On recrée une table temporaire avec le même schéma que le DataFrame
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {tmp}")
        df.head(0).to_sql(tmp, conn, if_exists="replace", index=False)
        df.to_sql(tmp, conn, if_exists="append", index=False)

        cols = list(df.columns)
        collist = ", ".join(cols)
        pk = ", ".join(pk_cols)

        # TODO: construire la partie "SET col = EXCLUDED.col" pour toutes les colonnes non PK
        # Exemple : "col1 = EXCLUDED.col1, col2 = EXCLUDED.col2, ..."
        updates = ", ".join(
            [
                f"{col} = EXCLUDED.{col}" for col in cols if col not in pk_cols
            ]
        )

        sql = text(f"""
            INSERT INTO {table} ({collist})
            SELECT {collist} FROM {tmp}
            ON CONFLICT ({pk}) DO UPDATE SET {updates}
        """)
        conn.execute(sql)
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {tmp}")

    return f"upserted {len(df)} rows into {table}"

@task
def validate_with_ge(table: str):
    """
    Exécute quelques expectations Great Expectations sur une table donnée.
    Si la validation échoue, on lève une exception pour faire échouer le flow.
    """
    import great_expectations as ge
    import pandas as pd
    from sqlalchemy import text

    # On récupère un échantillon (ou la table entière si elle est petite)
    with engine().begin() as conn:
        df = pd.read_sql(text(f"SELECT * FROM {table} LIMIT 50000"), conn)

    gdf = ge.from_pandas(df)

    # ---- Expectations spécifiques à chaque table ----
    if table == "users":
        gdf.expect_table_columns_to_match_set([
            "user_id","signup_date","user_gender","user_is_senior","has_family","has_dependents"
        ])
        gdf.expect_column_values_to_not_be_null("user_id")

    elif table == "subscriptions":
        gdf.expect_table_columns_to_match_set([
            "user_id", "months_active", "plan_stream_tv", "plan_stream_movies",
            "contract_type", "paperless_billing", "monthly_fee", "total_paid",
            "net_service", "add_on_security", "add_on_backup",
            "add_on_device_protect", "add_on_support"
        ])
        gdf.expect_column_values_to_not_be_null("user_id")
        gdf.expect_column_values_to_be_between("months_active", min_value=0)
        gdf.expect_column_values_to_be_between("monthly_fee", min_value=0)

    elif table == "usage_agg_30d":
        # Expectations pour usage_agg_30d
        gdf.expect_table_columns_to_match_set([
            "user_id","watch_hours_30d","avg_session_mins_7d","unique_devices_30d","skips_7d","rebuffer_events_7d"
        ])

        gdf.expect_column_values_to_not_be_null("user_id")
        gdf.expect_column_values_to_be_between("watch_hours_30d", min_value=0)
        gdf.expect_column_values_to_be_between("avg_session_mins_7d", min_value=0)

    else:
        # Table non reconnue : check minimal
        gdf.expect_column_values_to_not_be_null("user_id")

    result = gdf.validate()

    if not result.get("success", False):
        # On remonte la première expectation en échec pour faciliter le debug
        failed = [r for r in result["results"] if not r["success"]]
        if failed:
            exp_type = failed[0]["expectation_config"]["expectation_type"]
        else:
            exp_type = "unknown_expectation"
        raise AssertionError(f"GE validation failed for {table}: {exp_type}")

    return f"GE passed for {table}"

@task
def snapshot_month(as_of: str):
    """
    Crée (si besoin) les tables de snapshots et insère les données
    pour la date as_of donnée. Utilise une stratégie idempotente
    (ON CONFLICT DO NOTHING).
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS subscriptions_profile_snapshots (
      user_id TEXT,
      as_of DATE,
      months_active INT,
      monthly_fee NUMERIC,
      paperless_billing BOOLEAN,
      plan_stream_tv BOOLEAN,
      plan_stream_movies BOOLEAN,
      net_service TEXT,
      PRIMARY KEY (user_id, as_of)
    );

    CREATE TABLE IF NOT EXISTS usage_agg_30d_snapshots (
      user_id TEXT,
      as_of DATE,
      watch_hours_30d NUMERIC,
      avg_session_mins_7d NUMERIC,
      unique_devices_30d INT,
      skips_7d INT,
      rebuffer_events_7d INT,
      PRIMARY KEY (user_id, as_of)
    );

    CREATE TABLE IF NOT EXISTS payments_agg_90d_snapshots (
      user_id TEXT,
      as_of DATE,
      failed_payments_90d INT,
      PRIMARY KEY (user_id, as_of)
    );

    CREATE TABLE IF NOT EXISTS support_agg_90d_snapshots (
      user_id TEXT,
      as_of DATE,
      support_tickets_90d INT,
      ticket_avg_resolution_hrs_90d NUMERIC,
      PRIMARY KEY (user_id, as_of)
    );
    """

    sqls = [
        f"""
        INSERT INTO subscriptions_profile_snapshots
        (user_id, as_of, months_active, monthly_fee, paperless_billing,
         plan_stream_tv, plan_stream_movies, net_service)
        SELECT user_id, DATE '{as_of}', months_active, monthly_fee, paperless_billing,
               plan_stream_tv, plan_stream_movies, net_service
        FROM subscriptions
        ON CONFLICT (user_id, as_of) DO NOTHING;
        """,
        f"""
        INSERT INTO usage_agg_30d_snapshots
        (user_id, as_of, watch_hours_30d, avg_session_mins_7d,
         unique_devices_30d, skips_7d, rebuffer_events_7d)
        SELECT user_id, DATE '{as_of}', watch_hours_30d, avg_session_mins_7d,
               unique_devices_30d, skips_7d, rebuffer_events_7d
        FROM usage_agg_30d
        ON CONFLICT (user_id, as_of) DO NOTHING;
        """,
        f"""
        INSERT INTO payments_agg_90d_snapshots
        (user_id, as_of, failed_payments_90d)
        SELECT user_id, DATE '{as_of}', failed_payments_90d
        FROM payments_agg_90d
        ON CONFLICT (user_id, as_of) DO NOTHING;
        """,
        f"""
        INSERT INTO support_agg_90d_snapshots
        (user_id, as_of, support_tickets_90d, ticket_avg_resolution_hrs_90d)
        SELECT user_id, DATE '{as_of}', support_tickets_90d, ticket_avg_resolution_hrs_90d
        FROM support_agg_90d
        ON CONFLICT (user_id, as_of) DO NOTHING;
        """
    ]

    with engine().begin() as conn:
        # Création des tables de snapshots si nécessaire
        conn.exec_driver_sql(ddl)
        # Insertion des données pour as_of
        for sql in sqls:
            conn.exec_driver_sql(sql)

    return f"snapshots stamped for {as_of}"

@flow(name="ingest_month")
def ingest_month_flow(seed_dir: str = SEED_DIR, as_of: str = AS_OF):
    """
    Flow Prefect principal pour le mois donné.
    Dans cet exercice, on se concentre uniquement sur l'upsert des tables.
    La validation (Great Expectations) et les snapshots seront ajoutés plus tard.
    """
    # Upsert des tables de base
    upsert_csv("users",            f"{seed_dir}/users.csv",            ["user_id"])
    upsert_csv("subscriptions",    f"{seed_dir}/subscriptions.csv",    ["user_id"])
    upsert_csv("usage_agg_30d",    f"{seed_dir}/usage_agg_30d.csv",    ["user_id"])
    upsert_csv("payments_agg_90d", f"{seed_dir}/payments_agg_90d.csv", ["user_id"])
    upsert_csv("support_agg_90d",  f"{seed_dir}/support_agg_90d.csv",  ["user_id"])
    upsert_csv("labels",           f"{seed_dir}/labels.csv",           ["user_id"])

    # Validation GE (garde-fou avant les snapshots)
    validate_with_ge("users")
    validate_with_ge("subscriptions")
    validate_with_ge("usage_agg_30d")

    # Snapshots temporels
    snapshot_month(as_of)

    return f"Ingestion + validation + snapshots terminés pour {as_of}"


if __name__ == "__main__":
    ingest_month_flow()