# BorderCapControl Backend — Multi-Stage Dockerfile
# Stage 1: Abhängigkeiten mit Poetry bauen
# Stage 2: Schlankes Produktions-Image ohne Build-Tools

# ---------------------------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# System-Abhängigkeiten für Poetry und asyncpg (benötigt gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gcc \
        libpq-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-xlib-2.0-0 \
        libfontconfig1 \
        libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

# Poetry installieren
ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Nur pyproject.toml kopieren für Layer-Caching
COPY pyproject.toml ./

# Abhängigkeiten installieren (ohne Dev-Dependencies)
RUN poetry install --only main --no-root

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS final

# Minimale Runtime-Abhängigkeiten
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-xlib-2.0-0 \
        libfontconfig1 \
        libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

# Nicht-Root-User für Sicherheit
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Virtual Environment aus Builder kopieren
COPY --from=builder /app/.venv /home/appuser/app/.venv

# Applikationscode kopieren
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser alembic/ ./alembic/

# Python-Pfad auf venv setzen
ENV PATH="/home/appuser/app/.venv/bin:$PATH"
ENV PYTHONPATH="/home/appuser/app"

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
