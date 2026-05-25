"""
SQLAlchemy-Implementierung des Task-Repositories.
list_for_location() sortiert nach Priorität DESC (HIGH > MEDIUM > LOW), dann created_at ASC.
list_new_since() wird für SSE-Polling genutzt.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.models import TaskModel
from src.domain.tasks.entities import Task, TaskPriority, TaskStatus, TaskType
from src.ports.tasks.repository import AbstractTaskRepo


def _to_entity(model: TaskModel) -> Task:
    return Task(
        id=model.id,
        location_id=model.location_id,
        related_reservation_id=model.related_reservation_id,
        task_type=TaskType(model.task_type),
        priority=TaskPriority(model.priority),
        status=TaskStatus(model.status),
        title=model.title,
        body=model.body,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# CASE expression for priority ordering: HIGH=1, MEDIUM=2, LOW=3
_priority_order = case(
    {"HIGH": 1, "MEDIUM": 2, "LOW": 3},
    value=TaskModel.priority,
)


class SqlTaskRepo(AbstractTaskRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task: Task) -> Task:
        model = TaskModel(
            id=task.id,
            location_id=task.location_id,
            related_reservation_id=task.related_reservation_id,
            task_type=task.task_type.value,
            priority=task.priority.value,
            status=task.status.value,
            title=task.title,
            body=task.body,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def list_for_location(
        self, location_id: UUID, priority_filter: Optional[str] = None
    ) -> List[Task]:
        q = select(TaskModel).where(TaskModel.location_id == location_id)
        if priority_filter:
            q = q.where(TaskModel.priority == priority_filter)
        q = q.order_by(_priority_order.asc(), TaskModel.created_at.asc())
        result = await self._session.execute(q)
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_new_since(
        self, location_id: UUID, since: datetime
    ) -> List[Task]:
        result = await self._session.execute(
            select(TaskModel)
            .where(TaskModel.location_id == location_id)
            .where(TaskModel.created_at > since)
            .order_by(TaskModel.created_at.asc())
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def update(self, task_id: UUID, location_id: UUID, **kwargs) -> Task:
        result = await self._session.execute(
            select(TaskModel)
            .where(TaskModel.id == task_id)
            .where(TaskModel.location_id == location_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise HTTPException(status_code=404, detail="Task nicht gefunden")

        now = datetime.now(timezone.utc)
        for field, value in kwargs.items():
            if hasattr(model, field) and value is not None:
                setattr(model, field, value)
        model.updated_at = now
        await self._session.flush()
        return _to_entity(model)
