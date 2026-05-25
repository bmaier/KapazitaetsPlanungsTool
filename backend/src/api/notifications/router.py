"""
SSE-Benachrichtigungs-Endpoint.
GET /api/notifications/stream — sendet neue Tasks für die eigene Einrichtung alle 5 Sekunden.
Der Generator öffnet pro Poll-Zyklus eine eigene DB-Session (die Dependency-Session ist geschlossen).
"""
import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import LocationModel
from src.adapters.db.task_repo import SqlTaskRepo
from src.adapters.keycloak.jwt import get_current_user, get_location_context

router = APIRouter(tags=["notifications"])


@router.get("/notifications/stream")
async def notification_stream(
    location: LocationModel = Depends(get_location_context),
    user=Depends(get_current_user),
):
    """
    Server-Sent Events Stream für neue Tasks der eigenen Einrichtung.
    Pollt alle 5 Sekunden auf neue Tasks seit dem letzten Poll.
    HTTP 401 wenn kein gültiger Bearer-Token vorhanden (via get_current_user Dependency).
    """
    location_id = location.id

    async def generate():
        last_seen = datetime.now(timezone.utc)
        try:
            while True:
                await asyncio.sleep(5)
                # Capture timestamp BEFORE query to avoid missing tasks created during query
                query_since = last_seen
                last_seen = datetime.now(timezone.utc)
                async with AsyncSessionFactory() as session:
                    async with session.begin():
                        repo = SqlTaskRepo(session)
                        tasks = await repo.list_new_since(location_id, query_since)
                for task in tasks:
                    data = json.dumps(
                        {
                            "id": str(task.id),
                            "task_type": task.task_type.value,
                            "priority": task.priority.value,
                            "title": task.title,
                        }
                    )
                    yield f"data: {data}\n\n"
        except (GeneratorExit, asyncio.CancelledError):
            pass

    return StreamingResponse(generate(), media_type="text/event-stream")
