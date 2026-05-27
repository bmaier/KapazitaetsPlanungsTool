# BorderCapControl — Makefile
# Einheitlicher Workflow-Einstiegspunkt für die Entwicklungsumgebung.
#
# Verwendung:
#   make dev      Startet alle Services (inkl. Build) und wartet auf Healthchecks
#   make test     Führt Behave-Tests gegen die laufende Umgebung aus
#   make down     Stoppt alle Services und entfernt Volumes
#   make logs     Streamt Logs aller Services
#   make migrate  Führt ausstehende Alembic-Migrationen aus
#   make seed     Demo-Daten einspielen (nach make down + make dev nötig)

.PHONY: dev test down logs migrate seed frontend-install frontend-dev

# Auto-detect container runtime: prefer podman if available, fall back to docker.
# Override with: make dev RUNTIME=docker  or  make dev RUNTIME=podman
ifneq ($(shell command -v podman 2>/dev/null),)
RUNTIME ?= podman
else
RUNTIME ?= docker
endif
COMPOSE        ?= $(RUNTIME) compose
PROJECT         = kapzitaetsplanungstool
HEALTH_TIMEOUT ?= 120

# ---------------------------------------------------------------------------
# dev: Startet/aktualisiert alle Services und wartet auf Healthchecks
# ---------------------------------------------------------------------------
dev:
	@echo ">>> Bereinige Python-Bytecode-Cache (verhindert stale .pyc nach Rebuilds)..."
	@find backend/src -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null; true
	@echo ">>> Starte BorderCapControl Compose-Stack..."
	$(COMPOSE) up -d --build
	@echo ">>> Warte auf Healthchecks (max. $(HEALTH_TIMEOUT)s)..."
	@elapsed=0; result=1; \
	while [ $$elapsed -lt $(HEALTH_TIMEOUT) ]; do \
		statuses=$$($(RUNTIME) ps \
			--filter "label=com.docker.compose.project=$(PROJECT)" \
			--format "{{.Status}}" 2>/dev/null); \
		if [ -z "$$statuses" ]; then \
			echo "  Warte auf Container-Start... ($${elapsed}s)"; \
			sleep 5; elapsed=$$((elapsed + 5)); continue; \
		fi; \
		unhealthy=$$(echo "$$statuses" | grep -c "unhealthy" 2>/dev/null || echo 0); \
		if [ "$$unhealthy" -gt 0 ]; then \
			echo ""; \
			echo "!!! FEHLER: $$unhealthy Service(s) im Status 'unhealthy'. Logs:"; \
			$(COMPOSE) ps; \
			exit 1; \
		fi; \
		total=$$(echo "$$statuses" | wc -l | tr -d ' '); \
		healthy=$$(echo "$$statuses" | grep -c "(healthy)" 2>/dev/null || echo 0); \
		if [ "$$healthy" -ge "$$total" ] && [ "$$total" -gt 0 ]; then \
			echo ">>> Alle $$total Services sind bereit!"; \
			result=0; \
			break; \
		fi; \
		starting=$$(echo "$$statuses" | grep -c "health: starting" 2>/dev/null || echo 0); \
		echo "  Warte... ($${elapsed}s / $(HEALTH_TIMEOUT)s) — $$starting/$$total Service(s) starten noch ($$healthy healthy)"; \
		sleep 5; \
		elapsed=$$((elapsed + 5)); \
	done; \
	if [ $$result -ne 0 ]; then \
		echo "!!! TIMEOUT: Services nach $(HEALTH_TIMEOUT)s noch nicht bereit."; \
		$(COMPOSE) ps; \
		exit 1; \
	fi
	@echo ""
	@echo ">>> Service-Status:"
	@$(COMPOSE) ps
	@echo ""
	@echo ">>> Endpoints:"
	@echo "  Backend API:    http://localhost:8000/docs"
	@echo "  SKOS Service:   http://localhost:8001/docs"
	@echo "  Keycloak Admin: http://localhost:8080/admin (admin / admin_dev)"
	@echo "  PostgreSQL:     localhost:5432 (bordercap / bordercap_dev)"
	@echo "  Tileserver:     http://localhost:8082/"
	@echo ""
	@echo "  Hinweis: Nach 'make down' Demo-Daten mit 'make seed' neu einspielen."

# ---------------------------------------------------------------------------
# test: Führt Behave-Tests gegen die laufende Umgebung aus
# ---------------------------------------------------------------------------
test:
	@echo ">>> Führe Behave-Tests aus..."
	@if ! command -v behave >/dev/null 2>&1; then \
		echo ">>> Installiere Test-Abhängigkeiten..."; \
		pip install -r tests/requirements.txt; \
	fi
	cd tests && behave

# ---------------------------------------------------------------------------
# down: Stoppt alle Services und entfernt Volumes (sauberer Reset)
# ---------------------------------------------------------------------------
down:
	@echo ">>> Stoppe BorderCapControl Services..."
	$(COMPOSE) down -v
	@echo ">>> Fertig. Volumes entfernt. Demo-Daten mit 'make seed' neu einspielen."

# ---------------------------------------------------------------------------
# logs: Streamt Logs aller Services (Ctrl+C zum Beenden)
# ---------------------------------------------------------------------------
logs:
	$(COMPOSE) logs -f

# ---------------------------------------------------------------------------
# migrate: Führt ausstehende Alembic-Migrationen im Backend-Container aus
# ---------------------------------------------------------------------------
migrate:
	@echo ">>> Führe Alembic-Migrationen aus..."
	$(COMPOSE) exec backend alembic upgrade head
	@echo ">>> Migrationen abgeschlossen."

seed: ## Seed Demo-Daten in die DB einfügen (idempotent)
	python3 backend/seeds/demo_data.py

frontend-install: ## npm install im frontend/-Verzeichnis
	cd frontend && npm install

frontend-dev: ## Vite Dev-Server starten (Port 3000)
	cd frontend && npm run dev
