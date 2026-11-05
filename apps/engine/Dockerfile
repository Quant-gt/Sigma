FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    redis \
    httpx \
    polars \
    numba \
    numpy \
    pandas \
    pydantic \
    cryptography

COPY apps/engine ./apps/engine
COPY apps/api/app/schemas ./apps/api/app/schemas
COPY packages ./packages

CMD ["python", "-m", "apps.engine.scanner.engine"]
