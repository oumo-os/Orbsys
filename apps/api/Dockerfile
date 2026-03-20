FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast builds
RUN pip install uv --no-cache-dir

# Copy dependency spec first (layer cache)
COPY pyproject.toml .
RUN uv pip install --system --no-cache \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic[email] pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] bcrypt \
    nats-py httpx python-multipart boto3

# Copy source
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
