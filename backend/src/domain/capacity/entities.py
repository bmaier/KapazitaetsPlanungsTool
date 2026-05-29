"""
Domain Entities für das Kapazitätsmanagement.
Reine Python-Dataclasses — keine ORM-Abhängigkeit, kein FastAPI-Import.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
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
    room_type: str = "STANDARD"  # STANDARD | WARTEBEREICH
    labels: List[str] = field(default_factory=list)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


@dataclass
class Bed:
    id: UUID
    room_id: UUID
    bett_nummer: str
    bett_typ: BedType
    is_active: bool
    deaktiviert_ab: Optional[date] = None
    labels: List[str] = field(default_factory=list)
    valid_from: Optional[date] = None


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
