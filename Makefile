SHELL := /bin/zsh
COMPOSE_SAAS := docker compose --env-file .env.saas
COMPOSE_SELFHOSTED := docker compose --env-file .env.selfhosted

.PHONY: status dev dev-stop dev-logs api worker test lint format check migrate migrate-gen shell-db standalone pre-commit-install

status:
	git status --short
	git log --oneline -5

dev:
	$(COMPOSE_SAAS) up -d db redis api worker

dev-stop:
	$(COMPOSE_SAAS) stop api worker db redis

dev-logs:
	$(COMPOSE_SAAS) logs -f api worker

api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && python -m arq app.jobs.worker.WorkerSettings

test:
	cd backend && python -m pytest tests/ -v

lint:
	cd backend && ruff format --check . && ruff check .

format:
	cd backend && ruff format . && ruff check --fix .

check: lint test

migrate:
	cd backend && alembic upgrade head

migrate-gen:
	cd backend && alembic revision --autogenerate -m "$(name)"

shell-db:
	$(COMPOSE_SAAS) exec db psql -U postgres komoot_strava

standalone:
	docker compose -f docker-compose.yml up -d

pre-commit-install:
	pre-commit install
