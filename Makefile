# BorderCapControl — Makefile
# Einheitlicher Workflow-Einstiegspunkt für die Entwicklungsumgebung.
#
# Verwendung:
#   make dev      Startet alle Services; baut Images nur wenn noch nicht vorhanden
#   make build    Erzwingt Rebuild aller Images (nach Dockerfile-/Dep-Änderungen)
#   make test     Führt Behave-Tests gegen die laufende Umgebung aus
#   make down     Stoppt alle Services und entfernt Volumes
#   make logs     Streamt Logs aller Services
#   make migrate  Führt ausstehende Alembic-Migrationen aus
#   make seed     Demo-Daten einspielen (nach make down + make dev nötig)

.PHONY: dev build test down logs migrate seed

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
# Anzahl Core-Services mit Healthcheck (ohne Frontend, das im Hintergrund startet)
CORE_SERVICES  ?= 5

# ---------------------------------------------------------------------------
# _wait_healthy: Internes Makro — wartet bis CORE_SERVICES healthy sind
# ---------------------------------------------------------------------------
define WAIT_HEALTHY
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
		unhealthy=$$(echo "$$statuses" | grep -c "unhealthy" 2>/dev/null || true); \
		if [ "$${unhealthy:-0}" -gt 0 ]; then \
			echo ""; \
			echo "!!! FEHLER: $$unhealthy Service(s) unhealthy. Logs:"; \
			$(COMPOSE) ps; \
			exit 1; \
		fi; \
		healthy=$$(echo "$$statuses" | grep -c "(healthy)" 2>/dev/null || true); \
		if [ "$${healthy:-0}" -ge "$(CORE_SERVICES)" ]; then \
			echo ">>> $(CORE_SERVICES) Core-Services bereit! (Frontend startet im Hintergrund)"; \
			result=0; \
			break; \
		fi; \
		starting=$$(echo "$$statuses" | grep -c "health: starting" 2>/dev/null || true); \
		echo "  Warte... ($${elapsed}s / $(HEALTH_TIMEOUT)s) — $${healthy:-0}/$(CORE_SERVICES) healthy, $${starting:-0} starting"; \
		sleep 5; \
		elapsed=$$((elapsed + 5)); \
	done; \
	if [ $$result -ne 0 ]; then \
		echo "!!! TIMEOUT: Core-Services nach $(HEALTH_TIMEOUT)s noch nicht bereit."; \
		$(COMPOSE) ps; \
		exit 1; \
	fi
endef

define PRINT_ENDPOINTS
	@echo ""
	@echo ">>> Service-Status:"
	@$(COMPOSE) ps
	@echo ""
	@echo ">>> Endpoints:"
	@echo "  Frontend:       http://localhost:3000  (Vite startet ~60s nach Container-Start)"
	@echo "  Backend API:    http://localhost:8000/docs"
	@echo "  SKOS Service:   http://localhost:8001/docs"
	@echo "  Keycloak Admin: http://localhost:8080/admin (admin / admin_dev)"
	@echo "  PostgreSQL:     localhost:5432 (bordercap / bordercap_dev)"
	@echo "  Tileserver:     http://localhost:8082/"
	@echo ""
	@echo "  Hinweis: Nach 'make down' Demo-Daten mit 'make seed' neu einspielen."
endef

# ---------------------------------------------------------------------------
# dev: Startet alle Services (kein Rebuild — Volume-Mounts für Hot-Reload)
# Für expliziten Image-Rebuild nach Dockerfile-/Dep-Änderungen: make build
# ---------------------------------------------------------------------------
dev:
	@echo ">>> Bereinige Python-Bytecode-Cache..."
	@find backend/src -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null; true
	@echo ">>> Starte BorderCapControl Compose-Stack..."
	$(COMPOSE) up -d
	$(WAIT_HEALTHY)
	$(PRINT_ENDPOINTS)

# ---------------------------------------------------------------------------
# build: Erzwingt Rebuild aller Images (nach Dockerfile- oder Dep-Änderungen)
# ---------------------------------------------------------------------------
build:
	@echo ">>> Bereinige Python-Bytecode-Cache..."
	@find backend/src -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null; true
	@echo ">>> Baue Docker-Images und starte Stack..."
	$(COMPOSE) up -d --build
	$(WAIT_HEALTHY)
	$(PRINT_ENDPOINTS)

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
	$(RUNTIME) exec -w /home/appuser/app $(PROJECT)_backend_1 \
		/home/appuser/app/.venv/bin/python3 -m alembic upgrade head
	@echo ">>> Migrationen abgeschlossen."

seed: ## Seed Demo-Daten in die DB einfügen (idempotent)
	@echo ">>> Warte auf PostgreSQL (Port 5432)..."
	@elapsed=0; \
	while ! nc -z localhost 5432 2>/dev/null; do \
		if [ $$elapsed -ge 120 ]; then \
			echo "!!! TIMEOUT: PostgreSQL nach 120s nicht erreichbar."; exit 1; \
		fi; \
		echo "  Warte... ($${elapsed}s)"; \
		sleep 3; elapsed=$$((elapsed + 3)); \
	done; \
	echo ">>> PostgreSQL bereit — starte Seed..."
	python3 backend/seeds/demo_data.py
