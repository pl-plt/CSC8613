CI2 : Ingestion mensuelle, validation et snapshots
Ce TP prolonge le travail initié au TP1. Vous allez commencer à construire un pipeline d’ingestion de données pour un système de machine learning de bout en bout.

Le rapport du TP2 doit être rédigé en Markdown dans le fichier reports/rapport_tp2.md.
Vous devez réutiliser le même dépôt Git que pour le TP1 (ne créez pas un nouveau dépôt).
Avant de commencer ce TP, ajouter un tag tp1 sur votre dépôt correspondant à la fin du TP1.
Objectif global du TP :
Mettre en place une ingestion mensuelle pour les données month_000 et month_001, en utilisant :

PostgreSQL pour stocker les données structurées,
Prefect pour orchestrer le pipeline d’ingestion,
Great Expectations pour valider la qualité des données,
des snapshots temporels pour capturer l’état des données à la fin de chaque mois.
Le TP est à réaliser en environ 1h30 en séance. Vous pourrez compléter et nettoyer le rapport reports/rapport_tp2.md chez vous.

Mise en place du projet et du rapport
 Reprendre le dépôt du TP1
Vous devez réutiliser le même dépôt Git que pour le TP1. Placez-vous à la racine de ce dépôt (là où se trouvent api/, docker-compose.yml, reports/).

Vérifiez d’abord la structure minimale suivante :

ls
# Vous devriez voir au minimum :
# api/
# docker-compose.yml
# reports/
    
Puis affichez l’état du dépôt Git et copiez-coller la sortie dans votre rapport reports/rapport_tp2.md (dans une section que vous pourrez appeler par exemple État initial du dépôt).

git status
    
 Créer la structure minimale pour le TP2
Pour ce TP, nous allons progressivement nous rapprocher de l’architecture complète du projet. Commencez par créer les répertoires suivants :

db/init/
data/seeds/month_000/
data/seeds/month_001/
services/prefect/
reports/    (existe déjà normalement)
    
Créez ces répertoires depuis la racine du dépôt. Vérifiez ensuite qu’ils existent bien avec ls ou tree (si disponible), et ajoutez une courte capture (commande + sortie) dans votre rapport.

 Télécharger et extraire les données month_000 et month_001
Les données de ce TP sont fournies sous forme d’archives ZIP contenant des fichiers CSV. Téléchargez les deux archives depuis les liens suivants (depuis votre navigateur, en dehors des conteneurs Docker) :

Données month_000 : Télécharger month_000.zip
Données month_001 : Télécharger month_001.zip
Une fois les fichiers téléchargés, extrayez-les dans les répertoires prévus :

data/seeds/month_000/users.csv
data/seeds/month_000/subscriptions.csv
data/seeds/month_000/usage_agg_30d.csv
...

data/seeds/month_001/users.csv
data/seeds/month_001/subscriptions.csv
data/seeds/month_001/usage_agg_30d.csv
...
    
Vérifiez la liste des fichiers (par exemple avec ls data/seeds/month_000 et ls data/seeds/month_001) et copiez la liste obtenue dans votre rapport reports/rapport_tp2.md (par exemple dans une section Structure des données).

Base de données et docker-compose
 Créer le schéma de base de données dans db/init/001_schema.sql
Nous allons définir le schéma PostgreSQL qui servira de base à tout le système. Créez le fichier db/init/001_schema.sql et copiez-y le contenu suivant sans le modifier (aucun TODO ici) :

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  signup_date DATE,
  user_gender TEXT,
  user_is_senior BOOLEAN,
  has_family BOOLEAN,
  has_dependents BOOLEAN
);

CREATE TABLE IF NOT EXISTS subscriptions (
  user_id TEXT REFERENCES users(user_id),
  months_active INT,
  plan_stream_tv BOOLEAN,
  plan_stream_movies BOOLEAN,
  contract_type TEXT,
  paperless_billing BOOLEAN,
  monthly_fee NUMERIC,
  total_paid NUMERIC,
  net_service TEXT,
  -- hidden at start (left NULL)
  add_on_security BOOLEAN,
  add_on_backup BOOLEAN,
  add_on_device_protect BOOLEAN,
  add_on_support BOOLEAN,
  PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS usage_agg_30d (
  user_id TEXT REFERENCES users(user_id),
  watch_hours_30d NUMERIC,
  avg_session_mins_7d NUMERIC,
  unique_devices_30d INT,
  skips_7d INT,
  rebuffer_events_7d INT,
  PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS payments_agg_90d (
  user_id TEXT REFERENCES users(user_id),
  failed_payments_90d INT,
  PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS support_agg_90d (
  user_id TEXT REFERENCES users(user_id),
  support_tickets_90d INT,
  ticket_avg_resolution_hrs_90d NUMERIC,
  PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS labels (
  user_id TEXT REFERENCES users(user_id),
  churn_label BOOLEAN,
  PRIMARY KEY (user_id)
);
    
Sauvegardez le fichier, puis ajoutez une courte note dans votre rapport reports/rapport_tp2.md indiquant que le schéma a été créé.

 Créer et comprendre le fichier .env
Le fichier .env contient des variables d’environnement qui seront automatiquement injectées dans les conteneurs Docker. Cela permet de séparer la configuration (mots de passe, noms de base, etc.) du code.

À la racine du dépôt, créez un fichier nommé .env avec le contenu minimal suivant :

POSTGRES_USER=streamflow
POSTGRES_PASSWORD=streamflow
POSTGRES_DB=streamflow
    
Ces variables seront utilisées par le conteneur PostgreSQL (et plus tard par Prefect) pour se connecter à la base de données.

Ajoutez dans votre rapport une courte phrase expliquant à quoi sert un fichier .env dans un projet Docker.

 Mettre à jour docker-compose.yml
Pour ce TP, nous allons utiliser uniquement deux services : un service postgres pour la base de données et un service prefect (que nous utiliserons dans l’exercice suivant).

Adaptez votre fichier docker-compose.yml à la racine du projet pour qu’il contienne au minimum la configuration suivante :

services:
  postgres:
    image: postgres:16
    env_file: .env          # Utiliser les variables définies dans .env
    volumes:
      - ./db/init:/docker-entrypoint-initdb.d   # Monter les scripts d'init
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  prefect:
    build: ./services/prefect
    depends_on:
      - postgres
    env_file: .env          # Réutiliser les mêmes identifiants Postgres
    environment:
      PREFECT_API_URL: http://0.0.0.0:4200/api
      PREFECT_UI_URL: http://0.0.0.0:4200
      PREFECT_LOGGING_LEVEL: INFO
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - ./services/prefect:/opt/prefect/flows
      - ./data:/data:ro     # Rendre les CSV accessibles au conteneur Prefect

volumes:
  pgdata:
    
Vérifiez que votre fichier docker-compose.yml se trouve bien à la racine du dépôt (même niveau que le dossier db/). Vous pouvez montrer son contenu (ou un extrait) dans le rapport.

 Démarrer Postgres et vérifier les tables créées
Vous pouvez maintenant démarrer uniquement le service postgres :

docker compose up -d postgres
docker compose ps
    
Une fois le conteneur postgres en état Up, connectez-vous à la base de données depuis le conteneur :

docker compose exec postgres psql -U streamflow -d streamflow
    
Listez les tables existantes avec la commande \dt dans psql :

\dt
    
Copiez la sortie de \dt dans votre rapport reports/rapport_tp2.md et commentez brièvement, en une phrase par table, ce que représente chaque table du schéma.

Upsert des CSV avec Prefect (month_000)
 Créer le service Prefect : services/prefect/Dockerfile et services/prefect/requirements.txt
Nous allons maintenant créer un service prefect dédié à l’orchestration de notre pipeline d’ingestion. Créez le dossier services/prefect s’il n’existe pas déjà, puis ajoutez-y les deux fichiers suivants.

Fichier services/prefect/Dockerfile :

FROM prefecthq/prefect:3.0.3-python3.11

WORKDIR /opt/prefect/flows

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "-c", "prefect server start --host 0.0.0.0 --port 4200 & sleep 10 && prefect worker start --pool 'default-agent-pool' --work-queue 'default'"]
    
Fichier services/prefect/requirements.txt :

feast==0.56.0
mlflow==2.16.0
scikit-learn==1.7.2
pandas==2.3.3
SQLAlchemy==2.0.36
psycopg2-binary==2.9.11
psycopg-binary==3.2.12
psycopg-pool==3.2.7
psycopg==3.2.12
evidently==0.7.15
great_expectations==0.17.21
prefect==3.6.1
    
Copiez ces contenus tels quels. Nous n’allons pas utiliser toutes ces dépendances immédiatement, mais cela prépare les TP suivants.

Ajoutez dans votre rapport une courte note expliquant le rôle du conteneur prefect dans l’architecture (orchestration du pipeline d’ingestion).

 Créer le fichier services/prefect/ingest_flow.py (version TP)
Nous allons maintenant créer un premier flow Prefect qui lit les CSV de month_000 et les insère dans PostgreSQL en utilisant un upsert (INSERT ... ON CONFLICT DO UPDATE).

Créez le fichier services/prefect/ingest_flow.py avec le contenu suivant. Deux petites parties du code sont à compléter (marquées TODO) pour travailler la logique d’upsert.

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
                # à compléter
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


@flow(name="ingest_month")
def ingest_month_flow(seed_dir: str = SEED_DIR, as_of: str = AS_OF):
    """
    Flow Prefect principal pour le mois donné.
    Dans cet exercice, on se concentre uniquement sur l'upsert des tables.
    La validation (Great Expectations) et les snapshots seront ajoutés plus tard.
    """
    upsert_csv("users",            f"{seed_dir}/users.csv",            ["user_id"])
    upsert_csv("subscriptions",    f"{seed_dir}/subscriptions.csv",    ["user_id"])
    upsert_csv("usage_agg_30d",    f"{seed_dir}/usage_agg_30d.csv",    ["user_id"])
    upsert_csv("payments_agg_90d", f"{seed_dir}/payments_agg_90d.csv", ["user_id"])
    upsert_csv("support_agg_90d",  f"{seed_dir}/support_agg_90d.csv",  ["user_id"])
    upsert_csv("labels",           f"{seed_dir}/labels.csv",           ["user_id"])

    # Les étapes de validation et de snapshots viendront dans les exercices suivants.
    return f"Ingestion terminée pour {as_of}"


if __name__ == "__main__":
    ingest_month_flow()
    
Complétez les deux blocs TODO :

Conversion en booléen des colonnes de type booléen (`plan_stream_tv`, `plan_stream_movies`, `paperless_billing`) si elles sont présentes.
Construction de la chaîne updates utilisée dans le ON CONFLICT pour mettre à jour toutes les colonnes non clés primaires.
Décrivez brièvement dans votre rapport la logique de cette fonction upsert_csv (en quelques phrases).

 Lancer Prefect et l’ingestion de month_000
Vous pouvez maintenant construire l’image du service prefect et lancer le flow d’ingestion pour month_000.

Assurez-vous d’abord que le service postgres est démarré (voir exercice précédent), puis lancez également le service prefect :

docker compose up -d prefect
docker compose ps
    
Une fois le conteneur prefect en état Up, lancez le flow d’ingestion en lui passant les variables d’environnement adaptées pour le mois 000 :

docker compose exec \
  -e SEED_DIR=/data/seeds/month_000 \
  -e AS_OF=2024-01-31 \
  prefect python ingest_flow.py
    
Après l’exécution, connectez-vous à PostgreSQL pour vérifier que les données ont bien été insérées :

docker compose exec postgres psql -U streamflow -d streamflow
    
Puis exécutez les requêtes SQL suivantes :

SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM subscriptions;
    
Copiez les résultats dans votre rapport et commentez en une phrase : Combien de clients avons-nous après month_000 ?.

Validation des données avec Great Expectations
 Compléter la fonction validate_with_ge
Dans cet exercice, nous allons ajouter une étape de validation avec Great Expectations dans le flow d’ingestion. L’idée est de récupérer une table depuis PostgreSQL, d’appliquer quelques expectations, puis de faire échouer le flow si la validation ne passe pas.

Ouvrez le fichier services/prefect/ingest_flow.py et ajoutez-y la fonction suivante (par exemple après upsert_csv). Une partie est déjà écrite pour les tables users et subscriptions. Vous devez compléter les expectations pour la table usage_agg_30d (marquées par des commentaires).

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
        # À compléter : expectations pour usage_agg_30d
        # TODO: vérifier que les colonnes correspondent exactement à l'ensemble attendu
        # gdf.expect_table_columns_to_match_set([...])

        # TODO: ajouter quelques bornes raisonnables (par ex. >= 0) sur 1–2 colonnes numériques
        # gdf.expect_column_values_to_be_between("watch_hours_30d", min_value=0)
        # gdf.expect_column_values_to_be_between("avg_session_mins_7d", min_value=0)

        pass  # à supprimer lorsque vous aurez ajouté vos expectations

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
    
Complétez la partie elif table == "usage_agg_30d": :

Définir les colonnes attendues avec expect_table_columns_to_match_set.
Ajouter au moins une ou deux expectations de type expect_column_values_to_be_between pour vérifier que vos agrégats sont bien non négatifs (par exemple watch_hours_30d et avg_session_mins_7d doivent être ≥ 0).
Enfin, mettez à jour le flow pour appeler validate_with_ge après les upserts, par exemple :

@flow(name="ingest_month")
def ingest_month_flow(seed_dir: str = SEED_DIR, as_of: str = AS_OF):
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

    return f"Ingestion + validation terminées pour {as_of}"
    
Décrivez dans votre rapport, en quelques lignes, le rôle de validate_with_ge dans le pipeline.

 Relancer l’ingestion pour month_000 avec validation
Une fois la fonction validate_with_ge complétée et le flow mis à jour, relancez le flow d’ingestion pour month_000 comme précédemment :

docker compose exec \
  -e SEED_DIR=/data/seeds/month_000 \
  -e AS_OF=2024-01-31 \
  prefect python ingest_flow.py
    
Si vos expectations sont correctes et cohérentes avec les données, la pipeline doit se terminer sans erreur. Si une erreur Great Expectations apparaît, lisez attentivement le message pour comprendre quelle règle a été violée.

 Compléter le rapport : pourquoi ces bornes et comment protègent-elles le modèle ?
Dans votre fichier reports/rapport_tp2.md, ajoutez une section (par exemple Validation des données) dans laquelle vous :

copiez quelques lignes de vos expectations pour usage_agg_30d (par exemple les appels à expect_column_values_to_be_between) ;
expliquez, en quelques phrases, pourquoi vous avez choisi ces bornes, par exemple watch_hours_30d >= 0 ;
expliquez comment ces règles protègent votre futur modèle (exclusion de valeurs impossibles, détection d’exports corrompus, etc.).
Snapshots et ingestion month_001
 Compléter la fonction snapshot_month(as_of)
Nous allons maintenant ajouter une étape de création de snapshots temporels pour figer l’état des données à la fin de chaque mois. L’idée est de copier les données des tables live vers des tables *_snapshots avec un champ as_of.

Dans services/prefect/ingest_flow.py, ajoutez la fonction suivante. Elle crée d’abord les tables de snapshots si nécessaire, puis insère les données pour un mois donné. Un des blocs INSERT est à compléter par vous.

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
        # À compléter : suivre le même pattern pour payments_agg_90d_snapshots
        f"""
        INSERT INTO payments_agg_90d_snapshots
        (user_id, as_of, failed_payments_90d)
        SELECT
            -- À compléter : user_id, DATE '{as_of}', failed_payments_90d
            -- à partir de la table payments_agg_90d
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
    
Complétez le bloc d’insertion dans payments_agg_90d_snapshots en vous inspirant des autres blocs. Le but est d’avoir une ligne par utilisateur et par date as_of.

Ensuite, mettez à jour votre flow ingest_month_flow pour appeler snapshot_month(as_of) après la validation GE, par exemple :

@flow(name="ingest_month")
def ingest_month_flow(seed_dir: str = SEED_DIR, as_of: str = AS_OF):
    # Upsert des tables de base
    upsert_csv("users",            f"{seed_dir}/users.csv",            ["user_id"])
    upsert_csv("subscriptions",    f"{seed_dir}/subscriptions.csv",    ["user_id"])
    upsert_csv("usage_agg_30d",    f"{seed_dir}/usage_agg_30d.csv",    ["user_id"])
    upsert_csv("payments_agg_90d", f"{seed_dir}/payments_agg_90d.csv", ["user_id"])
    upsert_csv("support_agg_90d",  f"{seed_dir}/support_agg_90d.csv",  ["user_id"])
    upsert_csv("labels",           f"{seed_dir}/labels.csv",           ["user_id"])

    # Validation GE (garde-fou)
    validate_with_ge("users")
    validate_with_ge("subscriptions")
    validate_with_ge("usage_agg_30d")

    # Snapshots temporels
    snapshot_month(as_of)

    return f"Ingestion + validation + snapshots terminés pour {as_of}"
    
Ajoutez dans votre rapport une phrase expliquant ce que fait snapshot_month (en particulier le rôle de as_of).

 Ingestion de month_001 avec snapshots
Vous allez maintenant lancer l’ingestion pour le mois suivant month_001, avec une nouvelle valeur de AS_OF. Assurez-vous que postgres et prefect sont démarrés, puis exécutez :

docker compose exec \
  -e SEED_DIR=/data/seeds/month_001 \
  -e AS_OF=2024-02-29 \
  prefect python ingest_flow.py
    
Une fois le flow terminé sans erreur, connectez-vous à PostgreSQL et vérifiez qu’il existe bien des snapshots pour les deux dates 2024-01-31 et 2024-02-29, par exemple avec :

SELECT COUNT(*) FROM subscriptions_profile_snapshots WHERE as_of = '2024-01-31';
SELECT COUNT(*) FROM subscriptions_profile_snapshots WHERE as_of = '2024-02-29';
    
Copiez ces résultats dans votre rapport et commentez brièvement : avez-vous le même nombre de lignes ? davantage ? Pourquoi ?

 Compléter le rapport : schéma, explications et réflexion
Dans votre fichier reports/rapport_tp2.md, ajoutez une section de synthèse pour ce TP :

Un petit schéma (ASCII ou capture) montrant le pipeline complet
Une explication en quelques phrases :
Pourquoi on ne travaille pas directement sur les tables live pour entraîner un modèle ?
Pourquoi les snapshots sont importants pour éviter la data leakage et garantir la reproductibilité temporelle ?
Un court paragraphe de réflexion personnelle :
Qu’avez-vous trouvé le plus difficile dans la mise en place de l’ingestion ?
Quelles erreurs avez-vous rencontrées et comment les avez-vous corrigées ?
 Une fois le TP fini, ajoutez un tag tp2 à votre projet Git