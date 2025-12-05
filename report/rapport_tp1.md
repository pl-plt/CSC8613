# Telecom SudParis - CSC 8613 – Systèmes pour le machine learning

## TP1 : Introduction à la conteneurisation avec Docker

### Objectifs
Ce premier TP a pour objectifs de :
* Comprendre pourquoi la conteneurisation est essentielle dans un système de Machine Learning.
* Installer et vérifier le bon fonctionnement de Docker sur votre machine.
* Construire une première image Docker contenant une mini-API FastAPI.
* Exécuter un conteneur et exposer un service sur votre machine.
* Démarrer un mini-système multi-conteneurs avec Docker Compose (API + base de données).
* Apprendre à interagir avec des conteneurs (logs, exécution interactive, connexions).
* Préparer l’environnement qui servira de base aux TP suivants.

> Dans ce cours, tous les composants du système de Machine Learning (API, base de données, orchestrateur, Feature Store, monitoring, etc.) seront exécutés dans des conteneurs Docker. Il est donc essentiel de bien comprendre les bases avant de passer à l’ingestion de données et aux pipelines.

---

### 1. Installation de Docker et vérification de l’environnement

Dans cette première partie, vous allez installer Docker sur votre machine et vérifier que l’exécution de conteneurs fonctionne correctement.

> Selon votre système d’exploitation, les instructions peuvent varier légèrement. Si vous travaillez sous Windows, l’installation de WSL2 est fortement recommandée pour simplifier l’utilisation de Docker.

1. **Installez Docker Desktop** (Windows / macOS) ou **Docker Engine** (Linux) en suivant la documentation officielle : [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)

2. **Vérifiez votre installation** en exécutant la commande suivante dans un terminal :
   ```bash
   docker run hello-world
   ```
   ![dockerresult](static/img/runhelloworld.png)

3. **Listez maintenant les conteneurs présents sur votre machine** (en cours d'exécution ou arrêtés) :
   ```bash
   docker ps -a
   ```
   *Expliquez brièvement dans votre rapport ce que représente cette liste.*
   ![dockerresult](static/img/ps-a_1.png)
---

### 2. Premiers pas avec Docker : images et conteneurs

Dans cet exercice, vous allez découvrir les commandes Docker fondamentales en manipulant des conteneurs simples.

> Docker distingue les **images** (modèles figés contenant un environnement complet) et les **conteneurs** (instances actives d’une image). Vous manipulerez les deux tout au long du cours.

* **Question :** Expliquez en quelques phrases la différence entre une image Docker et un conteneur Docker. Cette réponse devra apparaître dans votre rapport final.

1. **Exécutez un conteneur très léger basé sur l’image alpine** et affichez un message dans la console :
   ```bash
   docker run alpine echo "Bonjour depuis un conteneur Alpine"
   ```
   *Que se passe-t-il après l'exécution de cette commande ? Expliquez brièvement dans votre rapport.*
>   On pull l'image depuis internet et on lance la commande 
   echo "Bonjour depuis un conteneur Alpine"
 
2. **Listez à nouveau les conteneurs présents sur votre machine** :
   ```bash
   docker ps -a
   ```
   *Vous devriez voir un conteneur alpine avec un statut `Exited`. Expliquez pourquoi dans votre rapport.*
   ![dockerresult](static/img/ps-a_2.png)

3. **Lancez un conteneur interactif basé sur Alpine** :
   ```bash
   docker run -it alpine sh
   ```
   À l’intérieur du conteneur, tapez les commandes suivantes :
   ```bash
   ls
   uname -a
   exit
   ```
   *Indiquez dans votre rapport ce que vous observez.*
>    On ouvre un shell interactif dans le conteneur alpine
   La commande ls liste les fichiers et dossiers présents dans le conteneur
   La commande uname -a affiche les informations sur le système d'exploitation du conteneur
   ![dockerresult](static/img/terminal_alpine.png)


---

### 3. Construire une première image Docker avec une mini-API FastAPI

Dans cet exercice, vous allez construire votre première image Docker à partir d’un petit service web écrit avec FastAPI. L’objectif est de comprendre la structure d’un Dockerfile et de créer une API simple exposant une route `/health`.

> FastAPI est un framework Python moderne utilisé dans de nombreux systèmes de Machine Learning pour exposer des modèles en production.

#### Étape 1 — Compléter le fichier `app.py`

On vous fournit ci-dessous un squelette de fichier `app.py` avec quelques éléments manquants. Complétez les zones indiquées.

* **Tâche :** Complétez le code afin que l’API expose une route `/health` qui renvoie un JSON `{"status": "ok"}`.

```python
# app.py

# TODO: importer FastAPI
from ________ import ________

# TODO: créer une instance FastAPI
app = ________()

# TODO: définir une route GET /health
_____________________
def health():
    return {"status": "ok"}
```

#### Étape 2 — Compléter le Dockerfile

Voici un Dockerfile partiellement rempli. Complétez les instructions manquantes pour :
* Définir une image de base adaptée ;
* Créer un répertoire de travail ;
* Copier votre fichier `app.py` ;
* Installer les dépendances requises (`fastapi`, `uvicorn`) ;
* Démarrer l’application au lancement du conteneur.

* **Tâche :** Complétez les lignes marquées `# TODO`.

```dockerfile
# Dockerfile

# TODO: choisir une image de base Python
FROM ____________

# TODO: définir le répertoire de travail dans le conteneur
WORKDIR ____________

# TODO: copier le fichier app.py
COPY ____________ ____________

# Installer FastAPI et Uvicorn
RUN pip install fastapi uvicorn

# TODO: lancer le serveur au démarrage du conteneur
___________ ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Étape 3 — Construire l'image Docker

Construisez maintenant l’image Docker à partir du Dockerfile avec la commande suivante :
```bash
docker build -t simple-api .
```
*Indiquez dans votre rapport que la construction s’est bien déroulée (capture d’écran recommandée).*
   ![dockerresult](static/img/simple_api_1.png)

---

### 4. Exécuter l’API FastAPI dans un conteneur Docker

Vous disposez maintenant d’une image Docker `simple-api` contenant une mini-API FastAPI. Dans cet exercice, vous allez exécuter cette image dans un conteneur et vérifier que l’API répond correctement sur votre machine.

#### Étape 1 — Lancer le conteneur

Lancez un conteneur à partir de l’image `simple-api` en exposant le port 8000 du conteneur sur le port 8000 de votre machine. Utilisez la commande suivante :
```bash
docker run -p 8000:8000 simple-api
```
*Expliquez dans votre rapport le rôle de l’option `-p 8000:8000`.*
> L'option -p 8000:8000 permet de mapper le port 8000 du conteneur au port 8000 de l'hôte, ce qui permet d'accéder à l'API depuis l'extérieur du conteneur.


#### Étape 2 — Tester l’endpoint `/health`

Dans un autre terminal (ou via votre navigateur), appelez l’endpoint `/health` de l’API :
```bash
curl http://localhost:8000/health
```
ou bien en ouvrant [http://localhost:8000/health](http://localhost:8000/health) dans un navigateur. Vérifiez que la réponse JSON correspond à ce qui était attendu.
*Ajoutez une capture d’écran de la réponse dans votre rapport.*
![statusok](static/img/status_localhost8000.png)
#### Étape 3 — Observer les conteneurs en cours d’exécution

Dans un autre terminal, affichez la liste des conteneurs en cours d’exécution :
```bash
docker ps
```
Identifiez la ligne correspondant au conteneur `simple-api` et notez dans votre rapport :
* le nom du conteneur,
* l'image utilisée,
* le port mappé.
> Le nom du conteneur : gracious_mendel
>
> L'image utilisée : simple-api
>
> Le port mappé :  8000->8000/tcp

![dockerresult](static/img/ps-a_3.png)

#### Étape 4 — Arrêter le conteneur

Arrêtez le conteneur en cours d’exécution depuis un autre terminal à l’aide de la commande :
```bash
docker stop <nom_ou_id_du_conteneur>
```
Puis vérifiez qu’il n’apparaît plus dans `docker ps`, mais qu’il est toujours visible dans `docker ps -a`.
*Expliquez brièvement la différence entre ces deux commandes dans votre rapport.*

> docker ps affiche les conteneurs en cours d'exécution tandis que docker ps -a affiche tous les conteneurs, qu'ils soient en cours d'exécution ou arrêtés.
---

### 5. Démarrer un mini-système multi-conteneurs avec Docker Compose

Dans cette partie, vous allez utiliser Docker Compose pour lancer plusieurs services en une seule commande : une API FastAPI (celle du TP) et une base de données PostgreSQL.

> Docker Compose permet de décrire l’architecture d’une application (services, réseaux, volumes, variables d’environnement, etc.) dans un fichier unique `docker-compose.yml`. Cela vous permet de reproduire facilement un environnement complet, ce qui est un prérequis pour les systèmes de Machine Learning.

#### Étape 1 — Préparer la structure des fichiers

Organisez votre répertoire de travail de la façon suivante :
```
.
├── api/
│   ├── app.py         # votre fichier FastAPI
│   └── Dockerfile     # votre Dockerfile pour l'API
└── docker-compose.yml # à créer à la racine
```

#### Étape 2 — Compléter le fichier `docker-compose.yml`

On vous propose ci-dessous un squelette de fichier `docker-compose.yml` incomplet. Votre objectif est de compléter les parties marquées `# TODO` pour :
* Définir un service `db` basé sur l’image officielle `postgres:16` ;
* Définir un service `api` qui utilise le Dockerfile du dossier `api/` ;
* Configurer les variables d’environnement pour PostgreSQL (utilisateur, mot de passe, base, tous égaux à `demo`) ;
* Exposer les ports nécessaires pour l’API et la base de données ;
* Spécifier que l’API dépend de la base de données.

* **Tâche :** Complétez le fichier `docker-compose.yml` ci-dessous.

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    environment:
      # TODO: définir l'utilisateur, le mot de passe et le nom de la base
      POSTGRES_USER: _______
      POSTGRES_PASSWORD: _______
      POSTGRES_DB: _______
    ports:
      # TODO: exposer le port PostgreSQL vers l'hôte
      - "____:5432"

  api:
    # TODO: construire l'image à partir du Dockerfile dans ./api
    build: _______
    ports:
      # TODO: exposer le port 8000 du conteneur vers l'hôte
      - "____:8000"
    depends_on:
      # TODO: indiquer que l'API dépend de la base de données
      - ____
```
> J'ai du modifier le docker-compose.yml pour corriger les erreurs de types (les ports doivent etre des entiers) et ajouter les parties manquantes.

#### Étape 3 — Démarrer la stack avec Docker Compose

À la racine de votre projet (là où se trouve `docker-compose.yml`), lancez les services en arrière-plan :
```bash
docker compose up -d
```
Puis affichez la liste des services gérés par Docker Compose :
```bash
docker compose ps
```
*Vérifiez dans votre rapport que les services `db` et `api` sont bien démarrés (capture d’écran recommandée).*
![dockerresult](static/img/compose-ps_1.png)
#### Étape 4 — Tester à nouveau l’endpoint `/health`

Vérifiez que l’endpoint `/health` de l’API est toujours accessible, cette fois-ci lorsque l’API est lancée via Docker Compose :
```bash
curl http://localhost:8000/health
```
ou via votre navigateur. *Ajoutez une capture d’écran dans votre rapport.*

![statusok](static/img/status_localhost8000_2.png)
#### Étape 5 — Arrêter proprement les services

Lorsque vous avez terminé, arrêtez et supprimez les conteneurs gérés par Docker Compose :
```bash
docker compose down
```
*Expliquez dans votre rapport la différence entre :*
* *Arrêter les services avec `docker compose down` ;*
* *Arrêter un conteneur individuel avec `docker stop <id>`.*
> docker compose down arrête et supprime tous les conteneurs, réseaux et volumes définis dans le fichier docker-compose.yml, tandis que docker stop <id> arrête uniquement un conteneur spécifique sans le supprimer.
---

### 6. Interagir avec la base de données PostgreSQL dans un conteneur

Dans un système de Machine Learning en production, les données sont presque toujours stockées dans une base de données ou un data warehouse. Dans ce TP, nous utilisons PostgreSQL, exécuté lui aussi dans un conteneur Docker.

> L’objectif ici n’est pas d’apprendre SQL en détail, mais de vérifier que vous savez vous connecter à une base PostgreSQL exécutée dans un conteneur Docker Compose.

**Pré-requis :** Assurez-vous que votre stack Docker Compose est bien démarrée :
```bash
docker compose up -d
docker compose ps
```

#### Étape 1 — Se connecter au conteneur PostgreSQL

Utilisez la commande suivante pour ouvrir un shell `psql` à l’intérieur du conteneur PostgreSQL :
```bash
docker compose exec db psql -U demo -d demo
```
*Expliquez dans votre rapport le rôle de chaque option (`exec`, `db`, `-U`, `-d`).*
> exec : permet d'exécuter une commande dans un conteneur en cours d'exécution
>
> db : nom du service défini dans docker-compose.yml
>
> -U : spécifie l'utilisateur de la base de données
>
> -d : spécifie le nom de la base de données à laquelle se connecter

#### Étape 2 — Exécuter quelques commandes SQL simples

Une fois connecté à `psql`, exécutez les commandes suivantes :
```sql
SELECT version();
```
Puis :
```sql
SELECT current_database();
```
*Notez dans votre rapport les résultats obtenus, et ajoutez une capture d’écran de la session `psql`.*
![psqlcmd](static/img/postgre_cmd_1.png)

#### Étape 3 — Comprendre la connexion depuis d'autres services

*Dans votre rapport, expliquez comment un autre service Docker (par exemple l’API) pourrait se connecter à la base de données PostgreSQL. Précisez :*
* *le hostname à utiliser ;*
* *le port ;*
* *l’utilisateur et le mot de passe ;*
* *le nom de la base.*

> Toutes ces infos sont définies dans le fichier docker-compose.yml:
>  - Le hostname à utiliser est db
> - Le port est 5432
> - L'utilisateur est demo et le mot de passe est demo
> - Le nom de la base est demo

#### Étape 4 — Nettoyer

Après vos tests, vous pouvez arrêter la stack :
```bash
docker compose down
```
Si vous souhaitez également supprimer les volumes associés (données persistantes), vous pouvez utiliser :
```bash
docker compose down -v
```
*Expliquez dans votre rapport la conséquence de l’option `-v`.*
> L'option -v supprime les volumes associés aux conteneurs, ce qui entraîne la perte des données persistantes stockées dans la base de données PostgreSQL.
---

### 7. Déboguer des conteneurs Docker : commandes essentielles et bonnes pratiques

Le débogage est une compétence essentielle lorsque vous travaillez avec des systèmes distribués ou multi-conteneurs. Dans cet exercice, vous allez découvrir quelques outils simples mais indispensables pour diagnostiquer des problèmes dans vos services Docker.

> Vous utiliserez ces commandes à chaque TP du module, que ce soit pour comprendre un échec d’ingestion, une API qui ne démarre pas, ou un modèle qui ne se charge plus.

#### Étape 1 — Afficher les logs d’un service

Affichez en continu les logs du service `api` exécuté par Docker Compose :
```bash
docker compose logs -f api
```
*Relevez dans votre rapport ce que vous observez lorsque :*
* *l’API démarre correctement ;*
* *l’API reçoit une requête `/health`.*
>J'ai d'abord fait un curl http://localhost:8000, d'ou le 404 not found, puis j'ai fait un curl http://localhost:8000/health d'ou le status ok
![dockerresult](static/img/log_api_1.png)

#### Étape 2 — Entrer dans un conteneur en cours d’exécution

Utilisez la commande ci-dessous pour ouvrir un shell `sh` dans le conteneur de l’API :
```bash
docker compose exec api sh
```
À l’intérieur du conteneur :
```bash
ls
python --version
exit
```
*Expliquez dans votre rapport ce que vous observez.*

> On ouvre un shell interactif dans le conteneur api
 La commande ls renvoie __app.py_ et app.py qui est le fichier ajouté via Dockerfile
 La commande python --version affiche la version 3.11.14
![dockerresult](static/img/exec_api_sh_1.png)
#### Étape 3 — Redémarrer un service

Redémarrez seulement le service `api` à l’aide de la commande suivante :
```bash
docker compose restart api
```
Vérifiez qu’après redémarrage, l’API est toujours accessible sur `/health`. *Expliquez dans votre rapport dans quelles situations un redémarrage est utile.*
> Un redémarrage est utile lorsque le service rencontre des problèmes temporaires ou des erreurs inattendues. Cela permet de réinitialiser l'état du service sans affecter les autres services dépendants.

#### Étape 4 — Conteneur qui ne démarre pas : diagnostic

Simulez un problème en introduisant volontairement une erreur dans votre fichier `app.py` (par exemple renommer `app` en `appi`), puis reconstruisez l’image :
```bash
docker build -t simple-api .
```
Relancez Docker Compose :
```bash
docker compose up -d --build
```
Observez les logs :
```bash
docker compose logs -f api
```
*Expliquez dans votre rapport comment vous avez identifié la cause de l’erreur.*
> Les logs ne nous ont pas données d'informations sur l'erreur, mais l'erreur s'est montrée a deux reprise via la commande `docker build` et `docker compose` 

#### Étape 5 — Supprimer des conteneurs et images

Supprimez tous les conteneurs arrêtés :
```bash
docker container prune
```
Supprimez toutes les images inutilisées :
```bash
docker image prune
```
*Expliquez dans votre rapport pourquoi il est utile de nettoyer régulièrement son environnement Docker.*
> Nettoyer régulièrement son environnement Docker permet de libérer de l'espace disque en supprimant les conteneurs et images inutilisés. Cela aide également à maintenir un environnement organisé et à éviter les conflits entre différentes versions d'images ou de conteneurs.
---

### 8. Questions de réflexion et consignes pour le rendu

Pour conclure ce premier TP, vous devez répondre à quelques questions de réflexion et préparer un rendu conforme aux consignes ci-dessous.

#### Questions de réflexion

1. **Expliquez pourquoi un notebook Jupyter n’est généralement pas adapté pour déployer un modèle de Machine Learning en production.** Votre réponse doit faire référence à au moins deux aspects vus durant ce TP (ex : reproductibilité, environnement, automatisation...).
> Un notebook Jupyter n'est généralement pas adapté pour déployer un modèle de Machine Learning en production pour plusieurs raisons. Premièrement, les notebooks ne garantissent pas la reproductibilité de l'environnement, car ils dépendent souvent de l'installation locale des bibliothèques et des versions spécifiques. Deuxièmement, les notebooks ne sont pas conçus pour l'automatisation et le déploiement à grande échelle, ce qui est essentiel en production. En utilisant des conteneurs Docker, on peut encapsuler l'application avec toutes ses dépendances, assurant ainsi un environnement cohérent et facilitant le déploiement automatisé.
2. **Expliquez pourquoi Docker Compose est un outil essentiel lorsque l’on manipule plusieurs services (API, base de données...).** Référencez au moins un avantage observé lors du TP.
> Docker Compose est un outil essentiel pour gérer plusieurs services car il permet de définir et de configurer tous les services nécessaires dans un seul fichier YAML. Cela facilite le démarrage, l'arrêt et la gestion des services en une seule commande, ce qui simplifie grandement le processus de déploiement. De plus, Docker Compose gère automatiquement les dépendances entre les services, assurant ainsi que les services sont démarrés dans le bon ordre.

#### Consignes pour le rendu

Le rendu doit contenir le code complet que vous avez produit, ainsi qu’un rapport écrit répondant aux questions ci-dessus et incluant les captures d’écran demandées dans les exercices.

1. **Créez un dépôt Git (privé ou public) contenant :**
   * le répertoire `api/` avec votre fichier `app.py` et votre Dockerfile ;
   * votre fichier `docker-compose.yml` ;
   * un dossier `reports/` contenant un fichier `rapport.md` rédigé en Markdown.

2. **Dans le fichier `rapport_tp1.md`, incluez :**
   * les réponses aux questions de réflexion ;
   * les captures d’écran demandées dans les exercices ;
   * toutes remarques personnelles sur les difficultés rencontrées.

3. **Envoyez le lien vers votre dépôt Git à votre enseignant au plus tard une semaine après la séance de TP.**

---
*Telecom SudParis - Institut Polytechnique de Paris*
