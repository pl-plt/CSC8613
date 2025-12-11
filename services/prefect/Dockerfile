FROM prefecthq/prefect:3.0.3-python3.11

WORKDIR /opt/prefect/flows

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "-c", "prefect server start --host 0.0.0.0 --port 4200 & sleep 10 && prefect worker start --pool 'default-agent-pool' --work-queue 'default'"]