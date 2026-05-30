"""
Domain-Entities für den Postkorb (Task-Inbox).
Reine Python-Datenklassen — kein I/O, kein FastAPI-Import, kein SQLAlchemy-Import.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class TaskType(str, Enum):
    RESERVATION_RECEIVED = "RESERVATION_RECEIVED"
    RESERVATION_CONFIRMED = "RESERVATION_CONFIRMED"
    RESERVATION_REJECTED = "RESERVATION_REJECTED"
    RESERVATION_CANCELLED = "RESERVATION_CANCELLED"
    RESERVATION_TRANSFERRED = "RESERVATION_TRANSFERRED"
    WOCHE_12_WARNUNG = "WOCHE_12_WARNUNG"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    DISMISSED = "DISMISSED"


@dataclass
class Task:
    id: uuid.UUID
    location_id: uuid.UUID
    related_reservation_id: Optional[uuid.UUID]
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    title: str
    body: str
    created_at: datetime
    updated_at: datetime
