"""
SQLAlchemy 2.0 ORM-Modelle für BorderCapControl.
Adapter-Schicht: kein Domain-Import, kein FastAPI-Import.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LocationModel(Base):
    __tablename__ = "locations"
    __table_args__ = {"schema": "capacity"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    adresse: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kontingent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notbett_kapazitaet: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    labels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    lat: Mapped[Optional[float]] = mapped_column(nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class RoomModel(Base):
    __tablename__ = "rooms"
    __table_args__ = {"schema": "capacity"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.locations.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geschlechts_designation: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    labels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class BedModel(Base):
    __tablename__ = "beds"
    __table_args__ = {"schema": "capacity"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.rooms.id"),
        nullable=False,
    )
    bett_nummer: Mapped[str] = mapped_column(String(50), nullable=False)
    bett_typ: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # KONTINGENT | NOTBETT
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    labels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    deaktiviert_ab: Mapped[Optional[date]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class OccupantModel(Base):
    __tablename__ = "occupants"
    __table_args__ = {"schema": "persons"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bed_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.beds.id"),
        nullable=False,
    )
    azr_id: Mapped[str] = mapped_column(String(50), nullable=False)
    alias_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geschlecht: Mapped[str] = mapped_column(String(10), nullable=False)
    belegung_start: Mapped[date] = mapped_column(Date, nullable=False)
    belegung_ende: Mapped[date] = mapped_column(Date, nullable=False)
    family_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    labels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class SystemSettingsModel(Base):
    __tablename__ = "system_settings"
    __table_args__ = {"schema": "capacity"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    eu_gesamtquote: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuditEventModel(Base):
    __tablename__ = "events"
    __table_args__ = {"schema": "audit"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ReservationRequestModel(Base):
    __tablename__ = "requests"
    __table_args__ = {"schema": "reservations"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requester_location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.locations.id"),
        nullable=False,
    )
    target_location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.locations.id"),
        nullable=False,
    )
    azr_id: Mapped[str] = mapped_column(String(50), nullable=False)
    geschlecht: Mapped[str] = mapped_column(String(10), nullable=False)
    geburtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    herkunftsland: Mapped[str] = mapped_column(String(3), nullable=False)
    belegung_start: Mapped[date] = mapped_column(Date, nullable=False)
    belegung_ende: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    confirmed_bed_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.beds.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class TaskModel(Base):
    __tablename__ = "inbox"
    __table_args__ = {"schema": "tasks"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capacity.locations.id"),
        nullable=False,
    )
    related_reservation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reservations.requests.id"),
        nullable=True,
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
