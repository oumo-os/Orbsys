FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

RUN uv pip install --system --no-cache \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg \
    pydantic pydantic-settings \
    python-jose[cryptography]

COPY src/ src/

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
