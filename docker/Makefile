# ── Can I Trust? — Makefile shortcuts ──────────────────────────
# Usage: make <target>

.PHONY: help up down build logs ps restart clean setup backup \
        dev dev-down shell-api shell-db migrate

COMPOSE      = docker compose
COMPOSE_DEV  = docker compose -f docker-compose.yml -f docker-compose.dev.yml
API_CONTAINER = cit_api
DB_CONTAINER  = cit_postgres

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*##"}{printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Production ──────────────────────────────────────────────────
setup:         ## First-time setup (generates certs, builds, starts)
	./setup.sh

up:            ## Start all production services
	$(COMPOSE) up -d

down:          ## Stop all services
	$(COMPOSE) down

build:         ## Rebuild all images
	$(COMPOSE) build --parallel

logs:          ## Stream all logs
	$(COMPOSE) logs -f

logs-api:      ## Stream API logs only
	$(COMPOSE) logs -f api

ps:            ## Show service status
	$(COMPOSE) ps

restart:       ## Restart a service: make restart s=api
	$(COMPOSE) restart $(s)

# ── Development ─────────────────────────────────────────────────
dev:           ## Start development stack (hot-reload, no nginx)
	$(COMPOSE_DEV) up -d

dev-down:      ## Stop development stack
	$(COMPOSE_DEV) down

dev-build:     ## Rebuild dev images
	$(COMPOSE_DEV) build

# ── Shell access ─────────────────────────────────────────────────
shell-api:     ## Open shell inside API container
	$(COMPOSE) exec $(API_CONTAINER) bash

shell-db:      ## Open psql inside postgres container
	$(COMPOSE) exec $(DB_CONTAINER) psql -U postgres -d can_i_trust

shell-redis:   ## Open redis-cli
	$(COMPOSE) exec cit_redis redis-cli

# ── Database ─────────────────────────────────────────────────────
migrate:       ## Run Alembic migrations
	$(COMPOSE) exec $(API_CONTAINER) alembic upgrade head

backup:        ## Backup PostgreSQL database
	./scripts/backup_db.sh

# ── Cleanup ──────────────────────────────────────────────────────
clean:         ## Remove containers, volumes, images
	$(COMPOSE) down -v --rmi local
	@echo "All containers, volumes, and local images removed."

clean-logs:    ## Clear log files
	rm -f logs/*.log

# ── Monitoring ──────────────────────────────────────────────────
stats:         ## Show container resource usage
	docker stats cit_api cit_postgres cit_redis cit_nginx cit_frontend
