FROM python:3.11-slim

WORKDIR /repo

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On garde le conteneur "vivant" pour pouvoir exécuter feast via docker compose exec
CMD ["bash", "-lc", "tail -f /dev/null"]
