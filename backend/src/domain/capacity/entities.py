"""
Domain Entities für das Kapazitätsmanagement.
Reine Python-Dataclasses — keine ORM-Abhängigkeit, kein FastAPI-Import.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from src.domain.capacity.value_objects import BedType, GenderDesignation


@dataclass
class Location:
    id: UUID
    name: str
    adresse: str
    kontingent: int
    notbett_kapazitaet: int
    is_active: bool


@dataclass
class Room:
    id: UUID
    location_id: UUID
    name: str
    geschlechts_designation: GenderDesignation
    is_active: bool


@dataclass
class Bed:
    id: UUID
    room_id: UUID
    bett_nummer: str
    bett_typ: BedType
    is_active: bool


@dataclass
class Occupancy:
    id: UUID
    bed_id: UUID
    azr_id: str
    alias_id: Optional[str]
    geschlecht: str
    belegung_start: date
    belegung_ende: date


@dataclass
class SystemSettings:
    eu_gesamtquote: int
