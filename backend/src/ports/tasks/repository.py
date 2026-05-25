"""
Port (ABC) für das Task-Repository.
Definiert die Schnittstelle zwischen Domäne/Anwendung und der DB-Adapter-Schicht.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.domain.tasks.entities import Task


class AbstractTaskRepo(ABC):

    @abstractmethod
    async def create(self, task: Task) -> Task:
        """Speichert eine neue Task in tasks.inbox."""

    @abstractmethod
    async def list_for_location(
        self, location_id: UUID, priority_filter: Optional[str] = None
    ) -> List[Task]:
        """
        Gibt Tasks für eine Einrichtung zurück.
        Sortierung: Priorität DESC (HIGH > MEDIUM > LOW), dann created_at ASC.
        """

    @abstractmethod
    async def list_new_since(
        self, location_id: UUID, since: datetime
    ) -> List[Task]:
        """Gibt Tasks zurück die nach 'since' erstellt wurden — für SSE-Polling."""

    @abstractmethod
    async def update(self, task_id: UUID, location_id: UUID, **kwargs) -> Task:
        """Aktualisiert Felder einer Task (priority, status). Nur wenn location_id passt."""
