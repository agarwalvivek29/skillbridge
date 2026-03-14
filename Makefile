# ─────────────────────────────────────────────────────────────────────────────
# SkillBridge — Development Makefile
# ─────────────────────────────────────────────────────────────────────────────

COMPOSE := docker compose -f infra/docker-compose.yml
API_DIR := services/api
WEB_DIR := apps/web
CONTRACTS_DIR := services/contracts

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra
infra: ## Start PostgreSQL + Redis
	$(COMPOSE) up -d postgres redis

.PHONY: infra.stop
infra.stop: ## Stop infrastructure containers
	$(COMPOSE) stop

.PHONY: infra.down
infra.down: ## Stop and remove infrastructure containers
	$(COMPOSE) down

.PHONY: infra.down.volumes
infra.down.volumes: ## Stop, remove containers AND delete volumes (destroys data)
	$(COMPOSE) down -v

.PHONY: infra.status
infra.status: ## Show infrastructure container status
	$(COMPOSE) ps

.PHONY: infra.logs
infra.logs: ## Tail infrastructure logs
	$(COMPOSE) logs -f

# ─────────────────────────────────────────────────────────────────────────────
# API (FastAPI)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: api
api: ## Start the API server (uvicorn with reload)
	cd $(API_DIR) && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: api.install
api.install: ## Install API dependencies
	cd $(API_DIR) && uv sync --all-extras

.PHONY: api.migrate
api.migrate: ## Run alembic migrations (head)
	cd $(API_DIR) && uv run alembic upgrade head

.PHONY: api.migrate.new
api.migrate.new: ## Create a new migration (usage: make api.migrate.new MSG="description")
	cd $(API_DIR) && uv run alembic revision --autogenerate -m "$(MSG)"

.PHONY: api.migrate.down
api.migrate.down: ## Downgrade one migration
	cd $(API_DIR) && uv run alembic downgrade -1

.PHONY: api.test
api.test: ## Run API tests
	cd $(API_DIR) && uv run pytest

.PHONY: api.test.cov
api.test.cov: ## Run API tests with coverage
	cd $(API_DIR) && uv run pytest --cov=src --cov-report=term-missing

.PHONY: api.lint
api.lint: ## Lint API code
	cd $(API_DIR) && uv run ruff check src/ tests/

.PHONY: api.format
api.format: ## Format API code
	cd $(API_DIR) && uv run ruff format src/ tests/

.PHONY: api.shell
api.shell: ## Open a Python shell with API context
	cd $(API_DIR) && uv run python

# ─────────────────────────────────────────────────────────────────────────────
# Web (Next.js)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: web
web: ## Start the web dev server (Next.js)
	cd $(WEB_DIR) && pnpm dev

.PHONY: web.install
web.install: ## Install web dependencies
	cd $(WEB_DIR) && pnpm install

.PHONY: web.build
web.build: ## Build the web app
	cd $(WEB_DIR) && pnpm build

.PHONY: web.lint
web.lint: ## Lint web code
	cd $(WEB_DIR) && pnpm lint

# ─────────────────────────────────────────────────────────────────────────────
# Contracts (Anchor / Solana)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: contracts.build
contracts.build: ## Build Anchor programs
	cd $(CONTRACTS_DIR) && anchor build

.PHONY: contracts.test
contracts.test: ## Run Anchor tests
	cd $(CONTRACTS_DIR) && anchor test

.PHONY: contracts.deploy
contracts.deploy: ## Deploy contracts to devnet
	cd $(CONTRACTS_DIR) && anchor deploy --provider.cluster devnet

# ─────────────────────────────────────────────────────────────────────────────
# Schema (protobuf)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: schema.gen
schema.gen: ## Regenerate protobuf bindings
	cd packages/schema && ./scripts/generate.sh

# ─────────────────────────────────────────────────────────────────────────────
# All-in-one
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: install
install: api.install web.install ## Install all dependencies

.PHONY: up
up: infra ## Start infra + API + web (API and web in background)
	@echo "── Starting API on :8000 ──"
	cd $(API_DIR) && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "── Starting Web on :3000 ──"
	cd $(WEB_DIR) && pnpm dev &
	@echo ""
	@echo "  API  → http://localhost:8000/docs"
	@echo "  Web  → http://localhost:3000"
	@echo "  DB   → postgresql://postgres:postgres@localhost:5432/skillbridge"
	@echo "  Redis→ redis://:redis@localhost:6379"
	@echo ""
	@echo "Run 'make down' to stop everything."
	@wait

.PHONY: down
down: ## Stop everything (infra + background processes)
	@-pkill -f "uvicorn src.main:app" 2>/dev/null || true
	@-pkill -f "next dev" 2>/dev/null || true
	$(COMPOSE) stop
	@echo "All stopped."

# ─────────────────────────────────────────────────────────────────────────────
# Quality
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Lint everything
	pnpm run lint
	cd $(API_DIR) && uv run ruff check src/ tests/

.PHONY: format
format: ## Format everything
	pnpm exec prettier --write "apps/**/*.{ts,tsx}" "packages/**/*.ts"
	cd $(API_DIR) && uv run ruff format src/ tests/

.PHONY: test
test: ## Run all tests
	cd $(API_DIR) && uv run pytest
	pnpm run test

# ─────────────────────────────────────────────────────────────────────────────
# Database utilities
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: db.psql
db.psql: ## Open psql shell to the dev database
	docker exec -it $$($(COMPOSE) ps -q postgres) psql -U postgres -d skillbridge

.PHONY: db.reset
db.reset: ## Drop and recreate the database, then run migrations
	docker exec -it $$($(COMPOSE) ps -q postgres) psql -U postgres -c "DROP DATABASE IF EXISTS skillbridge;"
	docker exec -it $$($(COMPOSE) ps -q postgres) psql -U postgres -c "CREATE DATABASE skillbridge;"
	cd $(API_DIR) && uv run alembic upgrade head
	@echo "Database reset complete."

.PHONY: redis.cli
redis.cli: ## Open redis-cli to the dev instance
	docker exec -it $$($(COMPOSE) ps -q redis) redis-cli -a redis

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."
