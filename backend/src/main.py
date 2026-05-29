"""
BorderCapControl Backend API — FastAPI-Einstiegspunkt.
Hexagonale Struktur: main.py orchestriert nur, keine Fachlogik hier.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx

from src.adapters.db.health import check_db_health
from src.api.audit.router import router as audit_router
from src.api.reports.router import router as reports_router
from src.jobs.scheduler import create_and_start, stop
from src.adapters.keycloak.jwt import get_current_user
from src.api.capacity.router import router as capacity_router
from src.api.map.router import router as map_router
from src.api.notifications.router import router as notification_router
from src.api.reservations.router import router as reservation_router
from src.api.suggestions.router import router as suggestion_router
from src.api.tasks.router import router as task_router
from src.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_and_start()
    yield
    stop(scheduler)


app = FastAPI(
    title="BorderCapControl API",
    version="0.1.0",
    description="Backend für die BAMF-Grenzverfahren-Kapazitätsplanung",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(capacity_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(map_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(reservation_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(task_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(notification_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(suggestion_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(reports_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(audit_router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/health")
async def health_check(response: Response):
    """
    Systemweiter Health-Check.
    Prüft DB-Verbindung und Keycloak-Erreichbarkeit.
    Gibt HTTP 200 zurück wenn alle Dienste ok sind, sonst HTTP 503.
    """
    db_ok = await check_db_health()

    keycloak_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.keycloak_url}/health/ready")
            keycloak_ok = resp.status_code == 200
    except Exception:
        pass

    all_ok = db_ok and keycloak_ok

    if not all_ok:
        response.status_code = 503

    return {
        "status": "ok" if all_ok else "degraded",
        "db": "connected" if db_ok else "unreachable",
        "keycloak": "reachable" if keycloak_ok else "unreachable",
    }
