.PHONY: up down dev infra migrate migration seed bootstrap lint fmt test install clean logs

# ── Infrastructure ────────────────────────────────────────────────────────────

up:
	cd infra && docker compose up -d

down:
	cd infra && docker compose down

down-v:
	cd infra && docker compose down -v  # wipes volumes

infra:
	cd infra && docker compose up -d postgres nats minio

logs:
	cd infra && docker compose logs -f api blind integrity

# ── Bootstrap (first run) ─────────────────────────────────────────────────────
# Run once after `make up` to create the schema and seed data.
# Usage:
#   make bootstrap
#   make bootstrap ORG=my-org HANDLE=founder PASSWORD=secret

ORG      ?= meridian
HANDLE   ?= founder
PASSWORD ?= change-me-2025

bootstrap: up
	@echo "Waiting for postgres to be ready..."
	@sleep 3
	cd infra && docker compose exec api alembic upgrade head
	cd infra && docker compose exec api \
		python -m src.scripts.seed \
		--org $(ORG) --handle $(HANDLE) --password $(PASSWORD)

# ── Dev (run all services locally, infra in docker) ──────────────────────────

dev: infra
	@echo "Starting all services locally (Ctrl+C to stop all)..."
	@trap 'kill 0' INT; \
	  (cd apps/api && uvicorn src.main:app --reload --port 8000) & \
	  (cd apps/blind && uvicorn src.main:app --reload --port 8001) & \
	  (cd services/integrity && python -m src.main) & \
	  (cd services/inferential && python -m src.main) & \
	  (cd services/insight && python -m src.main) & \
	  (cd apps/web && npm run dev) & \
	  wait

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	cd apps/api && alembic upgrade head

migrate-down:
	cd apps/api && alembic downgrade -1

migration:
	@[ -n "$(MSG)" ] || (echo "Usage: make migration MSG='describe change'" && exit 1)
	cd apps/api && alembic revision --autogenerate -m "$(MSG)"

seed:
	cd apps/api && python -m src.scripts.seed

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	cd apps/api && ruff check src/
	cd services/integrity && ruff check src/

fmt:
	cd apps/api && ruff format src/

test:
	cd apps/api && pytest

install:
	pip install -r apps/api/requirements.txt --break-system-packages 2>/dev/null || \
	pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings \
	  python-jose passlib bcrypt nats-py httpx python-multipart \
	  'pydantic[email]' --break-system-packages

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# ── Quick status check ────────────────────────────────────────────────────────

status:
	@echo "=== API health ==="
	@curl -sf http://localhost:8000/health | python3 -m json.tool || echo "API not running"
	@echo "=== Blind API health ==="
	@curl -sf http://localhost:8001/health | python3 -m json.tool || echo "Blind API not running"
	@echo "=== NATS ==="
	@curl -sf http://localhost:8222/healthz || echo "NATS not running"
