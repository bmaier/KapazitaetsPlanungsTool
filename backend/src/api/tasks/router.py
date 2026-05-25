"""
FastAPI APIRouter für Postkorb (Task-Inbox) Endpoints.
GET /api/tasks — gefiltert und sortiert nach X-Location-Id.
PATCH /api/tasks/{id} — Priorität oder Status ändern.
"""
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import LocationModel
from src.adapters.db.task_repo import SqlTaskRepo
from src.adapters.keycloak.jwt import get_location_context
from src.api.tasks.schemas import TaskPriorityUpdate, TaskResponse

router = APIRouter(tags=["tasks"])


async def _get_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


@router.get("/tasks")
async def list_tasks(
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> List[TaskResponse]:
    """
    Listet Tasks für die eigene Einrichtung.
    Sortierung: Priorität DESC (HIGH > MEDIUM > LOW), dann created_at ASC.
    Optional: ?priority=HIGH|MEDIUM|LOW
    """
    repo = SqlTaskRepo(session)
    tasks = await repo.list_for_location(location.id, priority_filter=priority)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: UUID,
    body: TaskPriorityUpdate,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> TaskResponse:
    """Aktualisiert Priorität oder Status einer Task. Nur eigene Tasks (location_id check)."""
    repo = SqlTaskRepo(session)
    updated = await repo.update(task_id, location.id, priority=body.priority, status=body.status)
    return TaskResponse.model_validate(updated)
