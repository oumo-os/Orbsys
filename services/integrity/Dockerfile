FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

RUN uv pip install --system --no-cache \
    sqlalchemy[asyncio] asyncpg nats-py httpx

COPY src/ src/

CMD ["python", "-m", "src.main"]
