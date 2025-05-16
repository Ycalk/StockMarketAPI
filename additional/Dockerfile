FROM python:3.13-slim-bullseye

WORKDIR /additional

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libsqlite3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir ./database
RUN pip install --no-cache-dir ./microkit
RUN pip install --no-cache-dir ./shared_models