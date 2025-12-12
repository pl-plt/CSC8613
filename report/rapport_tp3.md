## CI3 : Introduction à Feast et au Feature Store pour StreamFlow

Dans ce TP, vous allez connecter le pipeline de données existant (ingestion + snapshots) à un Feature Store (Feast) pour préparer l’entraînement futur d’un modèle de churn et commencer à exposer les features en production. Vous allez :

*   Ajouter un service Feast à l’architecture Docker existante.
*   Définir l’Entity principale (user), les DataSources PostgreSQL et les FeatureViews.
*   Appliquer la configuration Feast et vérifier la création du registre (registry.db).
*   Réaliser une première récupération offline de features pour construire un jeu de données d’entraînement (training\_df.csv).
*   Matérialiser les features dans le Online Store et tester une récupération online pour un utilisateur.
*   Intégrer un endpoint FastAPI minimal qui interroge Feast pour récupérer les features d’un utilisateur.
*   Documenter la démarche et une courte réflexion dans reports/rapport\_tp3.md.

### Setup initial, création du rapport et balisage Git

Avant de commencer le TP3, créez un tag Git afin de conserver une version propre de votre dépôt correspondant à la fin du TP2. Si cela n’a pas encore été fait, exécutez :

```bash
git tag -a tp2 -m "Fin du TP2" 
git push origin tp2
```

Cela permettra de revenir facilement à un état stable si nécessaire, et de comparer l’évolution du code entre les TP.

Si vous obtenez une erreur indiquant que le tag existe déjà, vous pouvez ignorer cette étape : cela signifie que vous aviez déjà balisé votre dépôt.

Créez le fichier de rapport du TP3 : reports/rapport\_tp3.md. Ce fichier accompagnera toutes vos réponses, extraits de commandes, schémas, et commentaires écrits. Copiez-y les sections suivantes, qui guideront votre rédaction :

```markdown
# Contexte 
# Mise en place de Feast 
# Définition du Feature Store 
# Récupération offline & online 
# Réflexion
```

Dans la section \# Contexte de votre rapport, écrivez un court paragraphe expliquant ou décrivant les points suivants :

*   Les données dont vous disposez déjà (snapshots mensuels pour deux périodes, tables utilisateurs, usage, abonnements, paiements, support…).
*   L’objectif du TP3 : brancher ces données au Feature Store Feast, récupérer des features en mode offline et online, et exposer un endpoint API simple utilisant ces features.

Le paragraphe doit tenir en quelques lignes et positionner clairement la finalité du TP dans le projet StreamFlow.

Vous pouvez relire vos rapports TP1 et TP2 pour rappeler brièvement ce qui a déjà été mis en place : ingestion, validations Great Expectations, snapshots, etc. Utilisez la syntaxe Markdown pour structurer clairement vos réponses.

> # Contexte
> Dans le cadre du projet StreamFlow, nous disposons de données relatives aux utilisateurs, à leur abonnement, à leur usage de la plateforme, à leurs paiements et à leurs interactions avec le support client. Ces données sont stockées dans une base PostgreSQL et des snapshots mensuels ont été créés pour capturer l'état des utilisateurs à différents moments dans le temps. L'objectif de ce TP3 est d'intégrer un Feature Store à l'aide de Feast afin de structurer et de gérer les features dérivées de ces données. Nous allons configurer Feast pour récupérer les features en mode offline, ce qui nous permettra de constituer un jeu de données d'entraînement pour un modèle de churn, ainsi qu'en mode online, afin d'exposer ces features via une API pour une utilisation en production.

### Ajout de Feast à l’architecture Docker

Nous allons d’abord préparer le service Feast côté code, puis l’ajouter à la composition Docker.  

1.  Créez l’arborescence suivante (si ce n’est pas déjà fait) :
    
    ```txt
    services/
        feast_repo/
            Dockerfile
            requirements.txt
            repo/
            feature_store.yaml
            entities.py        # (seront remplis dans l’exercice suivant)
            data_sources.py
            feature_views.py
            __init__.py 
    ```
    
2.  Dans services/feast\_repo/Dockerfile, copiez le contenu suivant, qui prépare un conteneur Python minimal pour exécuter Feast :
    
    ```Dockerfile
    FROM python:3.11-slim

    WORKDIR /repo

    RUN apt-get update && \
        apt-get install -y --no-install-recommends build-essential libpq-dev && \
        rm -rf /var/lib/apt/lists/*

    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # On garde le conteneur "vivant" pour pouvoir exécuter feast via docker compose exec
    CMD ["bash", "-lc", "tail -f /dev/null"]
    ```
    
3.  Dans services/feast\_repo/requirements.txt, ajoutez les dépendances minimales pour Feast :
    
    ```txt
    feast==0.56.0
    pandas==2.3.3
    psycopg2-binary==2.9.11
    SQLAlchemy==2.0.36
    psycopg==3.2.12
    psycopg-pool==3.2.7
    ```
    
4.  Dans services/feast\_repo/repo/feature\_store.yaml, définissez la configuration minimale du Feature Store pour utiliser PostgreSQL en offline et online store :
    
    ```yml
    project: streamflow
    provider: local
    registry: registry.db

    offline_store:
        type: postgres
        host: postgres
        port: 5432
        database: streamflow
        db_schema: public
        user: streamflow
        password: streamflow

    online_store:
        type: postgres
        host: postgres
        port: 5432
        database: streamflow
        db_schema: public
        user: streamflow
        password: streamflow

    entity_key_serialization_version: 2
    ```
    

Les fichiers entities.py, data\_sources.py et feature\_views.py seront complétés dans l’exercice suivant.

Vérifiez bien les chemins : le répertoire de travail à l’intérieur du conteneur Feast sera /repo. C’est là que Feast cherchera le fichier feature\_store.yaml et le reste de la configuration.

Modifiez maintenant votre docker-compose.yml pour ajouter un service feast. Dans le bloc services:, ajoutez un service en complétant les champs marqués \# TODO ci-dessous :

```yml
services:
  postgres:
    image: postgres:16
    env_file: .env
    volumes:
      - ./db/init:/docker-entrypoint-initdb.d
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  prefect:
    build: ./services/prefect
    depends_on:
      - postgres
    env_file: .env
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
      - ./data:/data:ro
  feast:
    build: ______________          # TODO: donnez le chemin de build
    depends_on:
        - postgres
    environment:
        FEAST_USAGE: "False"
    volumes:
        - ______________________  # TODO: monter le dossier ./services/feast_repo/repo dans /repo


volumes:
  pgdata:
    
```

Assurez-vous que :

*   le service feast construit l’image à partir de ./services/feast\_repo ;
*   le volume ./services/feast\_repo/repo est monté sur /repo à l’intérieur du conteneur.

Si vous n’êtes pas à l’aise avec la syntaxe YAML, faites attention à l’indentation : les blocs build, depends\_on, environment, volumes doivent être alignés sous le service feast.

Construisez les images et démarrez les services en arrière-plan :

```bash
docker compose up -d --build
```

1.  Vérifiez que le conteneur feast est bien démarré à l’aide de :
    
    ```bash
    docker compose ps
    ```
    
2.  Si le conteneur ne démarre pas, consultez ses logs :
    
    ```bash
    docker compose logs feast
    ```
    

Corrigez les éventuelles erreurs (chemins de volumes, indentation YAML, etc.), puis relancez docker compose up -d --build.

Dans la section \# Mise en place de Feast de votre reports/rapport\_tp3.md :

*   Collez la commande exacte que vous avez utilisée pour démarrer les services.
*   Écrivez 2–3 lignes expliquant le rôle du conteneur feast :
    *   où se trouve la configuration du Feature Store dans le conteneur ;
    *   comment vous allez l’utiliser (via docker compose exec feast ... pour lancer feast apply et feast materialize).

Vous pouvez vérifier que le fichier feature\_store.yaml est bien visible dans le conteneur feast en exécutant :

```bash
docker compose exec feast ls -R /repo
```
> # Mise en place de Feast
> Pour mettre en place Feast dans notre architecture Docker, nous avons ajouté un nouveau service nommé "feast" dans notre fichier docker-compose.yml. Ce service construit une image à partir du répertoire ./services/feast_repo et monte le volume ./services/feast_repo/repo sur /repo à l'intérieur du conteneur. Nous avons démarré les services en arrière-plan en utilisant la commande `docker compose up -d --build`.
> On peut voir que le conteneur est démarré grâce à la commandes ci-dessous:

```bash
$ docker compose ps
    NAME                 IMAGE             COMMAND                  SERVICE    CREATED          STATUS          PORTS
    csc8613-feast-1      csc8613-feast     "bash -lc 'tail -f /…"   feast      31 seconds ago   Up 30 seconds
    csc8613-postgres-1   postgres:16       "docker-entrypoint.s…"   postgres   20 hours ago     Up 30 seconds   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
    csc8613-prefect-1    csc8613-prefect   "/usr/bin/tini -g --…"   prefect    31 seconds ago   Up 30 seconds
```
> La configuration du Feature Store se trouve dans le fichier /repo/feature_store.yaml à l'intérieur du conteneur feast.
>
> Nous allons utiliser ce conteneur pour exécuter des commandes Feast telles que `feast apply` et `feast materialize` en utilisant la commande `docker compose exec feast <command>`.

> On peut vérifier que le fichier **feature_store.yaml** est bien visible dans le conteneur feast en exécutant la commande suivante:
```bash
$ docker compose exec feast ls -R /repo
/repo:
__init__.py  data_sources.py  entities.py  feature_store.yml  feature_view.py
```

### Définition de l’Entity, des DataSources et des FeatureViews (Feast)

**Définition de l’Entity user** L’Entity est la manière dont Feast identifie les entités métier pour lesquelles les features sont définies. Dans notre cas, l’entité centrale est l’utilisateur (client StreamFlow), identifié par user\_id.

1.  Ouvrez le fichier services/feast\_repo/repo/entities.py. Copiez-y le squelette:
    
    ```python
    from feast import Entity

    # TODO: définir l'entité principale "user"
    user = Entity(
        name=...,               # TODO
        join_keys=[...],        # TODO
        description=...,        # TODO (en français)
    )
    
    ```
    
2.  Complétez les champs:
    *   name : nom logique de l’entité ;
    *   join\_keys : liste de colonnes utilisées pour relier les features ;
    *   description : courte description en français du rôle de cette entité.
3.  Dans votre rapport (\# Définition du Feature Store), ajoutez un court paragraphe expliquant :
    *   ce qu’est une Entity dans Feast ;
    *   pourquoi user\_id est un bon choix de clé de jointure pour StreamFlow.

Rappelez-vous que les tables Postgres (par ex. users, subscriptions, ...\_snapshots) utilisent déjà la colonne user\_id comme clé principale. L’Entity Feast doit être cohérente avec ce schéma relationnel.

> # Définition du Feature Store
> Une Entity dans Feast est une représentation d'un objet métier fondamental (par ex un client, un produit, etc.) pour lequel nous souhaitons rattacher des features.
>
> Dans le cas de StreamFlow, user_id est une bonne clé de jointure car c'est l'identifiant unique présent dans toutes les tables postgres.

**Définition des DataSources PostgreSQL pour les snapshots** Dans le TP2, vous avez construit des tables de snapshots mensuels dans Postgres :

*   subscriptions\_profile\_snapshots
*   usage\_agg\_30d\_snapshots
*   payments\_agg\_90d\_snapshots
*   support\_agg\_90d\_snapshots

Chaque table contient typiquement les colonnes :

*   user\_id
*   as\_of (date du snapshot)
*   quelques colonnes de features (par ex. months\_active, watch\_hours\_30d, etc.)

1.  Ouvrez `services/feast_repo/repo/data_sources.py`. Copiez-y le squelette :
    
    ```python
    from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource

    # TODO: source pour subscriptions_profile_snapshots
    subs_profile_source = PostgreSQLSource(
        name="subs_profile_source",
        query="""
            SELECT user_id, as_of,
                -- TODO: colonnes de features
            FROM ...
        """,
        timestamp_field=...,  # TODO
    )

    # TODO: source pour usage_agg_30d_snapshots
    usage_agg_30d_source = PostgreSQLSource(
        name="usage_agg_30d_source",
        query="""
            SELECT user_id, as_of,
                -- TODO: colonnes de features
            FROM ...
        """,
        timestamp_field=...,  # TODO
    )

    # TODO: source pour payments_agg_90d_snapshots
    payments_agg_90d_source = PostgreSQLSource(
        name="payments_agg_90d_source",
        query="""
            SELECT user_id, as_of,
                -- TODO: colonnes de features
            FROM ...
        """,
        timestamp_field=...,  # TODO
    )

    # TODO: source pour support_agg_90d_snapshots
    support_agg_90d_source = PostgreSQLSource(
        name="support_agg_90d_source",
        query="""
            SELECT user_id, as_of,
                -- TODO: colonnes de features
            FROM ...
        """,
        timestamp_field=...,  # TODO
    )
    ```

2.  Complétez pour chaque PostgreSQLSource :
    *   FROM ... avec le nom de la table snapshot correspondante ;
    *   la liste des colonnes de features (voir les schémas dans snapshot\_month dans ingest\_flow.py) ;
    *   timestamp\_field avec la colonne servant de référence temporelle (as\_of).
3.  Vérifiez que chaque requête sélectionne uniquement :
    *   user\_id,
    *   as\_of,
    *   les colonnes de features pertinentes.
4.  Dans votre rapport, section \# Définition du Feature Store, indiquez :
    *   le nom d’une table de snapshot (par ex. usage\_agg\_30d\_snapshots) ;
    *   3–4 colonnes de features qu’elle contient.

> # Définition du Feature Store (2)
> Décrivons la table de snapshot `usage_agg_30d_snapshots` qui contient les colonnes suivantes:
> * user_id,
> * as_of,
> * watch_hours_30d,
> * avg_session_mins_7d,
> * unique_devices_30d,
> * skips_7d,
> * rebuffer_events_7d


**Définition des FeatureViews** Les FeatureViews regroupent les features par entité et par source. Nous allons créer quatre vues :

*   subs\_profile\_fv : profil d’abonnement ;
*   usage\_agg\_30d\_fv : usage de la plateforme ;
*   payments\_agg\_90d\_fv : paiements récents ;
*   support\_agg\_90d\_fv : interactions avec le support.

1.  Ouvrez services/feast\_repo/repo/feature\_views.py. Vous devriez voir un squelette proche de :
    
    ```python
    from feast import Field, FeatureView
    from feast.types import Float32, Int64, Bool, String
    from entities import user
    from data_sources import (
        subs_profile_source,
        usage_agg_30d_source,
        payments_agg_90d_source,
        support_agg_90d_source,
    )

    # TODO: FeatureView pour le profil d'abonnement
    subs_profile_fv = FeatureView(
        name="subs_profile_fv",
        entities=[user],
        ttl=None,
        schema=[
            # TODO: compléter les Field(...)
        ],
        source=subs_profile_source,
        online=True,
        tags={"owner": "mlops-course"},
    )

    # TODO: FeatureView pour l'usage 30j
    usage_agg_30d_fv = FeatureView(
        name="usage_agg_30d_fv",
        entities=[user],
        ttl=None,
        schema=[
            # TODO
        ],
        source=usage_agg_30d_source,
        online=True,
        tags={"owner": "mlops-course"},
    )

    # TODO: FeatureView pour les paiements 90j
    payments_agg_90d_fv = FeatureView(
        name="payments_agg_90d_fv",
        entities=[user],
        ttl=None,
        schema=[
            # TODO
        ],
        source=payments_agg_90d_source,
        online=True,
        tags={"owner": "mlops-course"},
    )

    # TODO: FeatureView pour le support 90j
    support_agg_90d_fv = FeatureView(
        name="support_agg_90d_fv",
        entities=[user],
        ttl=None,
        schema=[
            # TODO
        ],
        source=support_agg_90d_source,
        online=True,
        tags={"owner": "mlops-course"},
    )
    ```
    
2.  Complétez la liste des Field(...) pour chaque FeatureView avec les colonnes suivantes :
    *   subs\_profile\_fv :
    
    *   months\_active (Int64)
    *   monthly\_fee (Float32)
    *   paperless\_billing (Bool)
    *   plan\_stream\_tv (Bool)
    *   plan\_stream\_movies (Bool)
    *   net\_service (String)
    
    *   usage\_agg\_30d\_fv :
    
    *   watch\_hours\_30d (Float32)
    *   avg\_session\_mins\_7d (Float32)
    *   unique\_devices\_30d (Int64)
    *   skips\_7d (Int64)
    *   rebuffer\_events\_7d (Int64)
    
    *   payments\_agg\_90d\_fv :
    
    *   failed\_payments\_90d (Int64)
    
    *   support\_agg\_90d\_fv :
    
    *   support\_tickets\_90d (Int64)
    *   ticket\_avg\_resolution\_hrs\_90d (Float32)
    
3.  Une fois les FeatureViews complétées, exécutez dans le conteneur Feast :
    
    ```bash
    docker compose exec feast feast apply
    ```
    
4.  Vérifiez que :
    *   la commande se termine sans erreur ;
    *   le fichier registry.db est apparu dans services/feast\_repo/repo/.
```bash
$ docker compose exec feast feast apply
/usr/local/lib/python3.11/site-packages/feast/repo_config.py:278: DeprecationWarning: The serialization version below 3 are deprecated. Specifying `entity_key_serialization_version` to 3 is recommended.
warnings.warn(
/repo/entities.py:3: DeprecationWarning: Entity value_type will be mandatory in the next release. Please specify a value_type for entity 'user'.
user = Entity(
No project found in the repository. Using project name streamflow defined in feature_store.yaml
Applying changes for project streamflow
Deploying infrastructure for payments_agg_90d_fv
Deploying infrastructure for subs_profile_fv
Deploying infrastructure for support_agg_90d_fv
Deploying infrastructure for usage_agg_30d_fv

$ ls ./services/feast_repo/repo/
__init__.py  data_sources.py  entities.py  feature_store.yaml  feature_view.py  registry.db
```
5.  Dans votre rapport (\# Définition du Feature Store), expliquez en 2–3 phrases à quoi sert feast apply.

> # Définition du Feature Store (3)
> `feast apply` est une commande qui permet de déployer la configuration du Feature Store définie dans les fichiers Python (Entities, DataSources, FeatureViews) vers le registre de Feast. Cette commande crée ou met à jour les définitions des features dans le registre (registry.db) afin qu'elles soient prêtes à être utilisées pour la récupération offline et online.

Si vous obtenez une erreur ModuleNotFoundError depuis le conteneur Feast, vérifiez que : - vous exécutez bien la commande depuis le répertoire racine du projet ; - le volume ./services/feast\_repo/repo est correctement monté dans /repo.

### Utilisation offline et online des features (Feast + API)

**Récupération offline & création de training\_df.csv** Dans cette partie, vous allez :

*   construire un entity\_df pointant vers les utilisateurs présents dans les snapshots à la date AS\_OF = 2024-01-31 ;
*   utiliser Feast pour récupérer les features correspondantes via get\_historical\_features ;
*   joindre ces features avec les labels de churn ;
*   sauvegarder le jeu de données final dans data/processed/training\_df.csv.

Assurez-vous d’abord que le répertoire data/processed existe sur votre machine hôte :

```bash
mkdir -p data/processed
```

Vérifiez également que votre service prefect peut écrire dans /data à l’intérieur du conteneur. Si nécessaire, adaptez le volume dans docker-compose.yml :

```yml
prefect:
    build: ./services/prefect
    depends_on:
    - postgres
    env_file: .env
    environment:
    ...
    volumes:
    - ./services/prefect:/opt/prefect/flows
    - ./data:/data            # enlever :ro pour rendre le volume en écriture
    - ./services/feast_repo/repo:/repo          # Accès à Feast
    
```

Redémarrez ensuite les services :

```bash
docker compose up -d --build
```

Créez un nouveau script Python services/prefect/build\_training\_dataset.py. Ce script doit :

*   se connecter à PostgreSQL (nous réutilisons la logique de connexion de ingest\_flow.py) ;
*   construire un entity\_df à partir de la table subscriptions\_profile\_snapshots à la date as\_of = '2024-01-31' :

*   colonnes : user\_id, event\_timestamp (dérivée de as\_of) ;
*   récupérer les labels depuis la table labels (schéma simple : user\_id, churn\_label) ;
*   utiliser Feast (FeatureStore) pour faire un get\_historical\_features sur une liste de features, par exemple :

    *   subs\_profile\_fv:months\_active,
    *   subs\_profile\_fv:monthly\_fee,
    *   subs\_profile\_fv:paperless\_billing,
    *   usage\_agg\_30d\_fv:watch\_hours\_30d,
    *   usage\_agg\_30d\_fv:avg\_session\_mins\_7d,
    *   payments\_agg\_90d\_fv:failed\_payments\_90d ;

*   joindre les features avec les labels sur (user\_id, event\_timestamp) ;
*   sauvegarder le résultat final dans /data/processed/training\_df.csv.

Le squelette (avec TODO) :

```python
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
        # "subs_profile_fv:months_active",
        # ...
    ]

    hf = store.get_historical_features(
        entity_df=entity_df,
        features=features,
    ).to_df()

    # TODO: fusionner avec les labels
    df = _____.merge(________, on=[__________, ___________], how="inner")

    if df.empty:
        raise RuntimeError("Training set is empty after merge. Check AS_OF and labels.")

    os.makedirs("/data/processed", exist_ok=True)
    df.to_csv("/data/processed/training_df.csv", index=False)
    print(f"[OK] Wrote /data/processed/training_df.csv with {len(df)} rows")

if __name__ == "__main__":
    main()
```

Exécutez ce script dans le conteneur prefect :

```bash
docker compose exec prefect python build_training_dataset.py
```

Vérifiez sur votre machine hôte que le fichier data/processed/training\_df.csv a bien été créé. Dans votre rapport (\# Récupération offline & online) :

*   Ajoutez la commande que vous avez utilisée ;
*   Montrez les 5 premières lignes du fichier à l’aide de :

```bash
head -5 data/processed/training_df.csv
```

(copiez la sortie dans le rapport ou insérez une capture d’écran).


Toujours dans votre rapport, expliquez en 2–3 phrases comment Feast garantit la _temporal correctness_ (point-in-time correctness) lors de cette récupération offline. Appuyez-vous sur :

*   le champ timestamp\_field = "as\_of" dans vos DataSources ;
*   la structure de entity\_df (user\_id + event\_timestamp).

Rappel : pour que get\_historical\_features fonctionne correctement, entity\_df doit contenir au minimum les colonnes user\_id et event\_timestamp, et le timestamp\_field des DataSources doit pointer vers la bonne colonne temporelle (ici as\_of).

> # Récupération offline & online
> La commande utilisée pour exécuter le script de construction du jeu de données d'entraînement est la suivante:
>```bash
>$ docker compose exec prefect python build_training_dataset.py
>[OK] Wrote /data/processed/training_df.csv with 7043 rows
>```
> Les 5 premières lignes du fichier `data/processed/training_df.csv` sont les suivantes:
>```csv
>user_id,event_timestamp,months_active,monthly_fee,paperless_billing,watch_hours_30d,avg_session_mins_7d,failed_payments_90d,churn_label
>4686-GEFRM,2024-01-31,70,98.7,True,47.4896478506594,29.141044640845102,0,False
>8374-UULRV,2024-01-31,72,86.05,False,38.7037352652385,29.141044640845102,0,True
>3307-TLCUD,2024-01-31,17,34.4,False,32.3970207467829,29.141044640845102,0,True
>3957-SQXML,2024-01-31,34,24.95,False,30.9351129582808,29.141044640845102,0,False
>```
> 
> Feast garantit la "temporal correctness" lors de la récupération offline en utilisant le champ `timestamp_field` défini dans les DataSources, qui pointe vers la colonne `as_of`. Cela permet à Feast de s'assurer que les features récupérées pour chaque utilisateur sont basées uniquement sur les données disponibles jusqu'à la date spécifiée dans `event_timestamp` de l'`entity_df`.

**Matérialisation & récupération online** 

Nous allons maintenant :

*   matérialiser les features dans le Online Store ;
*   tester une récupération online pour un utilisateur donné.

Depuis votre machine hôte, lancez la matérialisation suivante :

```bash
docker compose exec feast feast materialize 2024-01-01T00:00:00 2024-02-01T00:00:00
```

Cette commande :

*   lit les données historiques dans l’Offline Store ;
*   remplit le Online Store avec les features des FeatureViews, pour les timestamps compris entre le 1er janvier et le 1er février 2024.

Toujours dans le conteneur feast, lancez un shell Python interactif ou créez un petit script, par exemple services/feast\_repo/repo/debug\_online\_features.py, pour tester get\_online\_features. Le script (avec TODO) :

```python
from feast import FeatureStore

store = FeatureStore(repo_path="/repo")

# TODO: choisir un user_id existant (par ex. depuis data/seeds/month_000/users.csv)
user_id = "0001"  # à adapter

features = [
    "subs_profile_fv:months_active",
    "subs_profile_fv:monthly_fee",
    "subs_profile_fv:paperless_billing",
]

feature_dict = store.get_online_features(
    features=features,
    entity_rows=[{"user_id": user_id}],
).to_dict()

print("Online features for user:", user_id)
print(feature_dict)
    
```

Exécutez-le dans le conteneur feast :

```bash
docker compose exec feast python /repo/debug_online_features.py
```

Choisissez un user\_id existant en regardant par exemple le contenu de data/seeds/month\_000/users.csv sur votre machine hôte.

Dans votre rapport (\# Récupération offline & online) :

*   copiez le dictionnaire retourné par get\_online\_features pour un utilisateur (sortie du script) ;
*   ajoutez une phrase pour expliquer ce qui se passe si vous interrogez un user\_id qui n’a pas de features matérialisées (par exemple : utilisateur inexistant ou en dehors de la fenêtre de matérialisation).

Si vous obtenez des valeurs None ou null pour certains champs, cela signifie que les features n’ont pas été trouvées pour la clé demandée (pas de ligne matérialisée dans le Online Store). Vérifiez alors que l’utilisateur existe bien dans les snapshots et que la fenêtre de matérialisation couvre la date concernée.

> # Récupération offline & online (2)
> La commande `docker compose exec feast python /repo/debug_online_features.py` retourne pour l'utilisateur "7590-VHVEG":
>```json
>{
>   'user_id': ['7590-VHVEG'],
>    'months_active': [1], 
>   'paperless_billing': [True], 
>   'monthly_fee': [29.850000381469727]
>}
>```
>
> Si l'utilisateur n'existe pas, les features retournées seront `None, indiquant qu'aucune donnée n'a été trouvée pour cet utilisateur dans le Online Store.


**Intégration minimale de Feast dans l’API** 

Nous allons maintenant connecter l’API au Feature Store pour exposer un endpoint simple qui renvoie les features d’un utilisateur. Modifiez votre docker-compose.yml pour ajouter un service api minimal (si ce n’est pas déjà fait). Ajoutez ce bloc sous les autres services :

```yml
 api:
    build: ./api
    env_file: .env
    depends_on:
      - postgres
      - feast
    ports:
      - "8000:8000"
    volumes:
      - ./api:/app
      - ./services/feast_repo/repo:/repo   # pour que l'API voie le repo Feast
```

Mettez à jour le api/Dockerfile :

```Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

    
```

Et créez le fichier api/requirements.txt :

```txt
fastapi
uvicorn
feast==0.56.0
pandas==2.3.3
psycopg2-binary==2.9.11
SQLAlchemy==2.0.36
psycopg==3.2.12
psycopg-pool==3.2.7
```

  
Ensuite, reconstruisez et redémarrez l’architecture :

```bash
docker compose up -d --build
```

Modifiez maintenant le fichier api/app.py (vous aviez un endpoint /health dans les TP précédents). Vous allez :

*   conserver un endpoint /health simple ;
*   initialiser un FeatureStore global avec repo\_path="/repo" ;
*   ajouter un endpoint GET /features/{user\_id} qui :

*   appelle get\_online\_features avec un petit sous-ensemble de features, par exemple :

*   subs\_profile\_fv:months\_active,
*   subs\_profile\_fv:monthly\_fee,
*   subs\_profile\_fv:paperless\_billing ;

*   retourne un JSON de la forme :

```python
{
  "user_id": "...",
  "features": {
    "months_active": ...,
    "monthly_fee": ...,
    "paperless_billing": ...
  }
}
```

Un exemple d’implémentation possible :

```python
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
```

Vérifiez que l’API fonctionne :

*   Assurez-vous que le service api est bien démarré :
    
    ```bash
    docker compose ps
    ```
    
*   Testez l’endpoint /health depuis votre machine :
    
    ```bach
    curl http://localhost:8000/health
    ```
    
    > Nous obtenons: 
    > ```json
    > {"status":"ok"}
    > ```
*   Choisissez un user\_id pour lequel vous savez que des features existent (par ex. un user du CSV data/seeds/month\_000/users.csv). Interrogez l’endpoint /features/{user\_id} :
    
    ```bash
    curl http://localhost:8000/features/7590-VHVEG
    ```
    
    Copiez la réponse JSON dans votre rapport, section \# Récupération offline & online.

> # Récupération offline & online (3)
> ```bash
> $ curl http://localhost:8000/features/7590-VHVEG
>```
> ```json
> {
>     "user_id": "7590-VHVEG",
>     "features": {
>         "user_id": "7590-VHVEG",
>         "paperless_billing": true,
>         "monthly_fee": 29.850000381469727,
>         "months_active": 1
>     }
> }
> ```
> On retrouve bien les features associées à l'utilisateur "7590-VHVEG".

Dans la section \# Réflexion de votre rapport, répondez brièvement (3–5 lignes) à la question suivante : _« En quoi ce endpoint /features/{user\_id}, basé sur Feast, nous aide-t-il à réduire le training-serving skew dans un système de ML en production ? »_

L’idée clé : l’API ne recalcule pas les features à la main, mais interroge les mêmes FeatureViews que celles utilisées pour générer le dataset d’entraînement. C’est cette centralisation et ce partage de logique qui limitent les divergences entre entraînement et production.

> # Réflexion
> Le endpoint `/features/{user_id}` basé sur Feast permet de réduire le training-serving skew en garantissant que les mêmes définitions de features sont utilisées à la fois lors de l'entraînement du modèle et lors de la prédiction en production. En centralisant la logique de calcul des features dans Feast, nous évitons les divergences potentielles qui pourraient survenir si les features étaient recalculées manuellement dans l'API. Cela assure une cohérence entre les données utilisées pour entraîner le modèle et celles utilisées pour faire des prédictions, ce qui est crucial pour la performance du modèle en production.

Pour terminer le TP, créez un tag Git marquant l’état de votre dépôt à la fin du TP3 :

```bash
git tag -a tp3 -m "Fin du TP3 - Feature Store et API" 
git push origin tp3
```

Notez dans votre rapport que le dépôt a été tagué avec tp3, afin de pouvoir revenir facilement à cet état dans les TP suivants.