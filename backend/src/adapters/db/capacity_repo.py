"""
SQLAlchemy-Implementierungen der Repository-Ports für das Kapazitätsmanagement.
Jede mutierende Operation schreibt einen Audit-Eintrag in derselben Session (atomares Commit).
"""
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.audit_service import write_audit
from src.adapters.db.models import (
    BedModel,
    LocationModel,
    OccupantModel,
    RoomModel,
    SystemSettingsModel,
)
from src.adapters.keycloak.jwt import UserContext
from src.domain.capacity.entities import (
    Bed,
    Location,
    Occupancy,
    Room,
    SystemSettings,
)
from src.domain.capacity.value_objects import BedType, GenderDesignation
from src.ports.capacity.repository import (
    BedRepo,
    LocationRepo,
    OccupancyRepo,
    RoomRepo,
    SystemSettingsRepo,
)


# ---------------------------------------------------------------------------
# Mapper-Funktionen: ORM-Modell ↔ Domain-Entity
# ---------------------------------------------------------------------------


def _to_location(m: LocationModel) -> Location:
    return Location(
        id=m.id,
        name=m.name,
        adresse=m.adresse,
        kontingent=m.kontingent,
        notbett_kapazitaet=m.notbett_kapazitaet,
        is_active=m.is_active,
    )


def _to_room(m: RoomModel) -> Room:
    return Room(
        id=m.id,
        location_id=m.location_id,
        name=m.name,
        geschlechts_designation=GenderDesignation(m.geschlechts_designation),
        is_active=m.is_active,
        room_type=m.room_type,
        labels=[],  # Labels werden via junction table separat geladen
        valid_from=m.valid_from,
        valid_until=m.valid_until,
    )


def _to_bed(m: BedModel) -> Bed:
    return Bed(
        id=m.id,
        room_id=m.room_id,
        bett_nummer=m.bett_nummer,
        bett_typ=BedType(m.bett_typ),
        is_active=m.is_active,
        deaktiviert_ab=m.deaktiviert_ab,
        labels=[],  # Labels werden via junction table separat geladen
        valid_from=m.valid_from,
    )


def _to_occupancy(m: OccupantModel) -> Occupancy:
    return Occupancy(
        id=m.id,
        bed_id=m.bed_id,
        azr_id=m.azr_id,
        alias_id=m.alias_id,
        geschlecht=m.geschlecht,
        belegung_start=m.belegung_start,
        belegung_ende=m.belegung_ende,
    )


# ---------------------------------------------------------------------------
# Repository-Implementierungen
# ---------------------------------------------------------------------------


class SqlLocationRepo(LocationRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, location: Location) -> Location:
        now = datetime.now(timezone.utc)
        model = LocationModel(
            id=location.id,
            name=location.name,
            adresse=location.adresse,
            kontingent=location.kontingent,
            notbett_kapazitaet=location.notbett_kapazitaet,
            is_active=location.is_active,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        await write_audit(
            self._session,
            "location.created",
            {
                "id": str(location.id),
                "name": location.name,
                "kontingent": location.kontingent,
            },
        )
        return _to_location(model)

    async def get_by_id(self, id: UUID) -> Optional[Location]:
        result = await self._session.execute(
            select(LocationModel).where(LocationModel.id == id)
        )
        model = result.scalar_one_or_none()
        return _to_location(model) if model else None

    async def list_active(self) -> List[Location]:
        result = await self._session.execute(
            select(LocationModel).where(LocationModel.is_active.is_(True))
        )
        return [_to_location(m) for m in result.scalars().all()]

    async def list_all(self) -> List[Location]:
        result = await self._session.execute(select(LocationModel))
        return [_to_location(m) for m in result.scalars().all()]

    async def sum_kontingent(self) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(LocationModel.kontingent), 0)).where(
                LocationModel.is_active.is_(True)
            )
        )
        return result.scalar_one()

    async def deactivate(self, id: UUID) -> None:
        result = await self._session.execute(
            select(LocationModel).where(LocationModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.is_active = False
            model.updated_at = datetime.now(timezone.utc)
            await write_audit(
                self._session,
                "location.deactivated",
                {"id": str(id)},
            )


class SqlRoomRepo(RoomRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, room: Room) -> Room:
        now = datetime.now(timezone.utc)
        model = RoomModel(
            id=room.id,
            location_id=room.location_id,
            name=room.name,
            geschlechts_designation=room.geschlechts_designation.value,
            room_type=room.room_type,
            is_active=room.is_active,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        await write_audit(
            self._session,
            "room.created",
            {
                "id": str(room.id),
                "location_id": str(room.location_id),
                "name": room.name,
                "geschlechts_designation": room.geschlechts_designation.value,
            },
        )
        return _to_room(model)

    async def get_by_id(self, id: UUID) -> Optional[Room]:
        result = await self._session.execute(
            select(RoomModel).where(RoomModel.id == id)
        )
        model = result.scalar_one_or_none()
        return _to_room(model) if model else None

    async def list_active_for_location(self, location_id: UUID) -> List[Room]:
        result = await self._session.execute(
            select(RoomModel).where(
                RoomModel.location_id == location_id,
                RoomModel.is_active.is_(True),
            )
        )
        return [_to_room(m) for m in result.scalars().all()]

    async def list_all_for_location(self, location_id: UUID) -> List[Room]:
        result = await self._session.execute(
            select(RoomModel).where(RoomModel.location_id == location_id)
        )
        return [_to_room(m) for m in result.scalars().all()]

    async def deactivate(self, id: UUID) -> None:
        result = await self._session.execute(
            select(RoomModel).where(RoomModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.is_active = False
            model.updated_at = datetime.now(timezone.utc)
            await write_audit(
                self._session,
                "room.deactivated",
                {"id": str(id)},
            )


class SqlBedRepo(BedRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, bed: Bed) -> Bed:
        now = datetime.now(timezone.utc)
        model = BedModel(
            id=bed.id,
            room_id=bed.room_id,
            bett_nummer=bed.bett_nummer,
            bett_typ=bed.bett_typ.value,
            is_active=bed.is_active,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        await write_audit(
            self._session,
            "bed.created",
            {
                "id": str(bed.id),
                "room_id": str(bed.room_id),
                "bett_nummer": bed.bett_nummer,
                "bett_typ": bed.bett_typ.value,
            },
        )
        return _to_bed(model)

    async def get_by_id(self, id: UUID) -> Optional[Bed]:
        result = await self._session.execute(
            select(BedModel).where(BedModel.id == id)
        )
        model = result.scalar_one_or_none()
        return _to_bed(model) if model else None

    async def list_active_for_room(self, room_id: UUID) -> List[Bed]:
        result = await self._session.execute(
            select(BedModel).where(
                BedModel.room_id == room_id,
                BedModel.is_active.is_(True),
            )
        )
        return [_to_bed(m) for m in result.scalars().all()]

    async def list_all_for_room(self, room_id: UUID) -> List[Bed]:
        result = await self._session.execute(
            select(BedModel).where(BedModel.room_id == room_id)
        )
        return [_to_bed(m) for m in result.scalars().all()]

    async def deactivate(self, id: UUID) -> None:
        result = await self._session.execute(
            select(BedModel).where(BedModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.is_active = False
            model.updated_at = datetime.now(timezone.utc)
            await write_audit(
                self._session,
                "bed.deactivated",
                {"id": str(id)},
            )


class SqlOccupancyRepo(OccupancyRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        occupancy: Occupancy,
        user: Optional[UserContext] = None,
        location_id: Optional[UUID] = None,
    ) -> Occupancy:
        now = datetime.now(timezone.utc)
        model = OccupantModel(
            id=occupancy.id,
            bed_id=occupancy.bed_id,
            azr_id=occupancy.azr_id,
            alias_id=occupancy.alias_id,
            geschlecht=occupancy.geschlecht,
            belegung_start=occupancy.belegung_start,
            belegung_ende=occupancy.belegung_ende,
            created_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        await write_audit(
            self._session,
            "OCCUPANCY_CREATED",
            {
                "id": str(occupancy.id),
                "bed_id": str(occupancy.bed_id),
                "azr_id": occupancy.azr_id,
                "belegung_start": occupancy.belegung_start.isoformat(),
                "belegung_ende": occupancy.belegung_ende.isoformat(),
            },
            user=user,
            location_id=location_id,
            entity_type="OCCUPANCY",
            entity_id=occupancy.azr_id,
        )
        return _to_occupancy(model)

    async def get_by_id(self, id: UUID) -> Optional[Occupancy]:
        result = await self._session.execute(
            select(OccupantModel).where(OccupantModel.id == id)
        )
        model = result.scalar_one_or_none()
        return _to_occupancy(model) if model else None

    async def get_active_for_bed(self, bed_id: UUID) -> Optional[Occupancy]:
        result = await self._session.execute(
            select(OccupantModel).where(
                OccupantModel.bed_id == bed_id,
                OccupantModel.belegung_ende >= date.today(),
            )
        )
        model = result.scalars().first()
        return _to_occupancy(model) if model else None

    async def delete(
        self,
        id: UUID,
        user: Optional[UserContext] = None,
        location_id: Optional[UUID] = None,
        grund: Optional[str] = None,
    ) -> None:
        result = await self._session.execute(
            select(OccupantModel).where(OccupantModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            payload: dict = {
                "id": str(id),
                "bed_id": str(model.bed_id),
                "azr_id": model.azr_id,
            }
            if grund:
                payload["grund"] = grund
            await write_audit(
                self._session,
                "OCCUPANCY_DELETED",
                payload,
                user=user,
                location_id=location_id,
                entity_type="OCCUPANCY",
                entity_id=model.azr_id,
            )
            await self._session.delete(model)


class SqlSystemSettingsRepo(SystemSettingsRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SystemSettings:
        result = await self._session.execute(
            select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            # Fallback: Singleton anlegen falls noch nicht vorhanden
            now = datetime.now(timezone.utc)
            model = SystemSettingsModel(id=1, eu_gesamtquote=0, updated_at=now)
            self._session.add(model)
            await self._session.flush()
        return SystemSettings(eu_gesamtquote=model.eu_gesamtquote)

    async def set_eu_quota(self, quota: int) -> None:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = SystemSettingsModel(id=1, eu_gesamtquote=quota, updated_at=now)
            self._session.add(model)
        else:
            model.eu_gesamtquote = quota
            model.updated_at = now
        await self._session.flush()
        await write_audit(
            self._session,
            "system_settings.eu_quota_updated",
            {"eu_gesamtquote": quota},
        )
