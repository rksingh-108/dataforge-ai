# =============================================================================
# DataForge AI — developer commands
# -----------------------------------------------------------------------------
# `make` with no arguments lists every target. These targets are the canonical
# way to run things; CI calls the same scripts so "works locally" means
# "works in CI".
# =============================================================================
SHELL := /bin/bash
.DEFAULT_GOAL := help

API_DIR := apps/api
AI_DIR := apps/ai-service
WEB_DIR := apps/web

.PHONY: help
help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Stack -------------------------------------------------------------------
.PHONY: init
init: ## Create .env from the template if missing
	@test -f .env || (cp .env.example .env && echo "Created .env — fill in the secrets before starting.")

.PHONY: up
up: init ## Start the full stack in the background
	docker compose up --build -d
	@echo "web http://localhost:3000 · api http://localhost:8000 · ai http://localhost:8001"

.PHONY: down
down: ## Stop the stack
	docker compose down

.PHONY: clean
clean: ## Stop the stack and delete volumes (DESTROYS local data)
	docker compose down -v

.PHONY: logs
logs: ## Tail logs from all services
	docker compose logs -f --tail=100

.PHONY: ps
ps: ## Show service status
	docker compose ps

# --- Database ----------------------------------------------------------------
.PHONY: migrate
migrate: ## Apply database migrations
	docker compose exec api python manage.py migrate --noinput

.PHONY: makemigrations
makemigrations: ## Create new migrations
	docker compose exec api python manage.py makemigrations

.PHONY: seed
seed: ## Seed the development organization and users
	docker compose exec api python manage.py seed_development

.PHONY: db-shell
db-shell: ## Open a psql shell on the platform database
	docker compose exec db psql -U $${POSTGRES_USER:-dataforge} -d $${POSTGRES_DB:-dataforge}

# --- Tests -------------------------------------------------------------------
.PHONY: test
test: test-backend test-ai test-web ## Run every test suite

.PHONY: test-backend
test-backend: ## Run the Django test suite
	bash scripts/testing/run-backend-tests.sh

.PHONY: test-ai
test-ai: ## Run the AI service test suite
	bash scripts/testing/run-ai-tests.sh

.PHONY: test-web
test-web: ## Run frontend unit tests
	cd $(WEB_DIR) && npm run test

.PHONY: test-security
test-security: ## Run the cross-service security tests
	bash scripts/testing/run-security-tests.sh

.PHONY: test-integration
test-integration: ## Run cross-service integration tests
	bash scripts/testing/run-integration-tests.sh

# --- Quality -----------------------------------------------------------------
.PHONY: lint
lint: ## Lint the Python services and type-check the frontend
	.venv/bin/ruff check $(API_DIR) $(AI_DIR) scripts || python -m ruff check $(API_DIR) $(AI_DIR) scripts
	cd $(WEB_DIR) && npm run typecheck

.PHONY: typecheck
typecheck: ## Type-check the frontend
	cd $(WEB_DIR) && npm run typecheck

.PHONY: format
format: ## Auto-format Python code
	python -m ruff format $(API_DIR) $(AI_DIR)
	python -m ruff check --fix $(API_DIR) $(AI_DIR)

.PHONY: security
security: ## Run local security checks (bandit, pip-audit, boundary rules)
	bash scripts/dev/run-security-checks.sh

.PHONY: check-boundaries
check-boundaries: ## Verify service boundary rules
	python scripts/dev/check_boundaries.py

.PHONY: ci
ci: check-boundaries test lint ## Run everything CI runs
