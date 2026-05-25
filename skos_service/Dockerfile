# SKOS Codelisten Service — Dockerfile
# Multi-Stage: Poetry-Installation als root, dann Non-Root-Runtime

FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_NO_INTERACTION=1

# Poetry als root installieren (vor User-Switch, kein Root-Rollback nötig)
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app
COPY pyproject.toml ./
RUN poetry install --only main --no-root

FROM python:3.11-slim AS final

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

COPY --from=builder /app/.venv /home/appuser/app/.venv
COPY --chown=appuser:appuser src/ ./src/

ENV PATH="/home/appuser/app/.venv/bin:$PATH"
ENV PYTHONPATH="/home/appuser/app"

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
