"""
Abstract Repository-Interfaces (Ports) für das Kapazitätsmanagement.
Definieren den Vertrag zwischen Domain und Infrastruktur — keine Implementierung.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.capacity.entities import (
    Bed,
    Location,
    Occupancy,
    Room,
    SystemSettings,
)


class LocationRepo(ABC):
    @abstractmethod
    async def create(self, location: Location) -> Location: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Location]: ...

    @abstractmethod
    async def list_active(self) -> List[Location]: ...

    @abstractmethod
    async def list_all(self) -> List[Location]: ...

    @abstractmethod
    async def sum_kontingent(self) -> int: ...

    @abstractmethod
    async def deactivate(self, id: UUID) -> None: ...


class RoomRepo(ABC):
    @abstractmethod
    async def create(self, room: Room) -> Room: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Room]: ...

    @abstractmethod
    async def list_active_for_location(self, location_id: UUID) -> List[Room]: ...

    @abstractmethod
    async def list_all_for_location(self, location_id: UUID) -> List[Room]: ...

    @abstractmethod
    async def deactivate(self, id: UUID) -> None: ...


class BedRepo(ABC):
    @abstractmethod
    async def create(self, bed: Bed) -> Bed: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Bed]: ...

    @abstractmethod
    async def list_active_for_room(self, room_id: UUID) -> List[Bed]: ...

    @abstractmethod
    async def list_all_for_room(self, room_id: UUID) -> List[Bed]: ...

    @abstractmethod
    async def deactivate(self, id: UUID) -> None: ...


class OccupancyRepo(ABC):
    @abstractmethod
    async def create(self, occupancy: Occupancy) -> Occupancy: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Occupancy]: ...

    @abstractmethod
    async def get_active_for_bed(self, bed_id: UUID) -> Optional[Occupancy]: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...


class SystemSettingsRepo(ABC):
    @abstractmethod
    async def get(self) -> SystemSettings: ...

    @abstractmethod
    async def set_eu_quota(self, quota: int) -> None: ...
