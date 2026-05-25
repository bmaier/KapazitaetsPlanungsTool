"""
Pydantic-Schemas für die Postkorb (Task-Inbox) API.
"""
from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class TaskResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    related_reservation_id: Optional[uuid.UUID]
    task_type: str
    priority: str
    status: str
    title: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskPriorityUpdate(BaseModel):
    priority: Optional[str] = None   # "LOW", "MEDIUM", "HIGH"
    status: Optional[str] = None     # "OPEN", "IN_PROGRESS", "DONE", "DISMISSED"
