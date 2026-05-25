# BorderCapControl — Makefile
# Einheitlicher Workflow-Einstiegspunkt für die Entwicklungsumgebung.
#
# Verwendung:
#   make dev      Startet alle Services (inkl. Build) und wartet auf Healthchecks
#   make test     Führt Behave-Tests gegen die laufende Umgebung aus
#   make down     Stoppt alle Services und entfernt Volumes
#   make logs     Streamt Logs aller Services
#   make migrate  Führt ausstehende Alembic-Migrationen aus

.PHONY: dev test down logs migrate seed frontend-install frontend-dev

# Maximale Wartezeit auf Healthchecks in Sekunden
HEALTH_TIMEOUT ?= 120

# ---------------------------------------------------------------------------
# dev: Startet/aktualisiert alle Services und wartet auf Healthchecks
# ---------------------------------------------------------------------------
dev:
	@echo ">>> Starte BorderCapControl Docker-Compose-Umgebung..."
	docker compose up -d --build
	@echo ">>> Warte auf alle Healthchecks (max. $(HEALTH_TIMEOUT)s)..."
	@elapsed=0; \
	result=1; \
	while [ $$elapsed -lt $(HEALTH_TIMEOUT) ]; do \
		unhealthy=$$(docker compose ps 2>/dev/null | grep -c "unhealthy" 2>/dev/null || echo 0); \
		if [ "$$unhealthy" -gt 0 ]; then \
			echo ""; \
			echo "!!! FEHLER: $$unhealthy Service(s) im Status 'unhealthy'. Logs:"; \
			docker compose ps; \
			exit 1; \
		fi; \
		still_starting=$$(docker compose ps 2>/dev/null | grep -cE "(health: starting|starting)" 2>/dev/null || echo 0); \
		if [ "$$still_starting" = "0" ]; then \
			echo ">>> Alle Services sind bereit!"; \
			result=0; \
			break; \
		fi; \
		echo "  Warte... ($${elapsed}s / $(HEALTH_TIMEOUT)s) — $$still_starting Service(s) initialisieren noch"; \
		sleep 5; \
		elapsed=$$((elapsed + 5)); \
	done; \
	if [ $$result -ne 0 ]; then \
		echo "!!! TIMEOUT: Services nach $(HEALTH_TIMEOUT)s noch nicht bereit."; \
		docker compose ps; \
		exit 1; \
	fi
	@echo ""
	@echo ">>> Service-Status:"
	@docker compose ps
	@echo ""
	@echo ">>> Endpoints:"
	@echo "  Backend API:    http://localhost:8000/docs"
	@echo "  SKOS Service:   http://localhost:8001/docs"
	@echo "  Keycloak Admin: http://localhost:8080/admin (admin / admin_dev)"
	@echo "  PostgreSQL:     localhost:5432 (bordercap / bordercap_dev)"
	@echo "  Tileserver:     http://localhost:8082/"

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
	docker compose down -v
	@echo ">>> Fertig. Volumes entfernt."

# ---------------------------------------------------------------------------
# logs: Streamt Logs aller Services (Ctrl+C zum Beenden)
# ---------------------------------------------------------------------------
logs:
	docker compose logs -f

# ---------------------------------------------------------------------------
# migrate: Führt ausstehende Alembic-Migrationen im Backend-Container aus
# ---------------------------------------------------------------------------
migrate:
	@echo ">>> Führe Alembic-Migrationen aus..."
	docker compose exec backend alembic upgrade head
	@echo ">>> Migrationen abgeschlossen."

seed: ## Seed Demo-Daten in die DB einfügen (idempotent)
	python3 backend/seeds/demo_data.py

frontend-install: ## npm install im frontend/-Verzeichnis
	cd frontend && npm install

frontend-dev: ## Vite Dev-Server starten (Port 3000)
	cd frontend && npm run dev
