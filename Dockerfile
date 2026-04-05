FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY babysitter/requirements.txt babysitter/requirements.txt
RUN pip install --no-cache-dir -r babysitter/requirements.txt

COPY babysitter/ babysitter/
COPY config.docker.yaml /app/config.yaml

EXPOSE 7890 9090

ENV PYTHONUNBUFFERED=1

CMD ["python", "babysitter/main.py", "/app/config.yaml"]
