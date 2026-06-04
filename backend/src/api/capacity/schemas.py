"""
Pydantic v2 Request/Response-Schemas für die Kapazitäts-API.
DSGVO: OccupancyCreate hat kein name-Feld — nur azr_id, alias_id, geschlecht, Daten.
"""
from datetime import date
from typing import Optional
from uuid import UUID

import math
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.capacity.value_objects import BedType, GenderDesignation


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    adresse: str = Field(default="", max_length=500)
    kontingent: int = Field(..., ge=0)
    notbett_kapazitaet: int = Field(default=0, ge=0)


class LocationResponse(BaseModel):
    id: UUID
    name: str
    adresse: str
    kontingent: int
    notbett_kapazitaet: int
    is_active: bool
    labels: list[str] = []
    lat: Optional[float] = None
    lon: Optional[float] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    geschlechts_designation: GenderDesignation = GenderDesignation.D
    room_type: str = "STANDARD"  # STANDARD | WARTEBEREICH


class RoomResponse(BaseModel):
    id: UUID
    location_id: UUID
    name: str
    geschlechts_designation: GenderDesignation
    room_type: str = "STANDARD"
    is_active: bool
    labels: list[str] = []
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Bed
# ---------------------------------------------------------------------------


class BedCreate(BaseModel):
    bett_nummer: str = Field(..., min_length=1, max_length=50)
    bett_typ: BedType


class BedResponse(BaseModel):
    id: UUID
    room_id: UUID
    bett_nummer: str
    bett_typ: BedType
    is_active: bool
    labels: list[str] = []
    deaktiviert_ab: Optional[date] = None
    valid_from: Optional[date] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Occupancy
# ---------------------------------------------------------------------------


class OccupancyCreate(BaseModel):
    """
    DSGVO-konform: kein name-Feld.
    Nur technische Identifikatoren (azr_id, alias_id) und Belegungszeitraum.
    """
    azr_id: str = Field(..., min_length=1, max_length=50)
    alias_id: Optional[str] = Field(None, max_length=100)
    geschlecht: GenderDesignation
    belegung_start: date
    belegung_ende: date
    geschlecht_mismatch_grund: Optional[str] = None
    verlegung_grund: Optional[str] = None

    @model_validator(mode="after")
    def ende_after_start(self) -> "OccupancyCreate":
        if self.belegung_ende <= self.belegung_start:
            raise ValueError("belegung_ende muss nach belegung_start liegen")
        return self


class OccupancyResponse(BaseModel):
    id: UUID
    bed_id: UUID
    azr_id: str
    alias_id: Optional[str]
    geschlecht: str
    belegung_start: date
    belegung_ende: date

    model_config = {"from_attributes": True}


class OccupancyPeriodUpdate(BaseModel):
    belegung_start: date
    belegung_ende: date

    @model_validator(mode="after")
    def ende_after_start(self) -> "OccupancyPeriodUpdate":
        if self.belegung_ende <= self.belegung_start:
            raise ValueError("belegung_ende muss nach belegung_start liegen")
        return self


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------


class EuQuotaUpdate(BaseModel):
    eu_gesamtquote: int = Field(..., ge=0)


# ---------------------------------------------------------------------------
# Location Summary (Dashboard)
# ---------------------------------------------------------------------------


class LocationUpdate(BaseModel):
    kontingent: Optional[int] = Field(None, ge=0)
    notbett_kapazitaet: Optional[int] = Field(None, ge=0)
    adresse: Optional[str] = Field(None, max_length=500)


class LocationUpdateRequest(BaseModel):
    name: Optional[str] = None
    adresse: Optional[str] = None
    kontingent: Optional[int] = None
    notbett_kapazitaet: Optional[int] = None
    labels: Optional[list[str]] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

    @field_validator('lat')
    @classmethod
    def validate_lat(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (not math.isfinite(v) or v < -90 or v > 90):
            raise ValueError('Breitengrad muss eine endliche Zahl zwischen -90 und 90 sein.')
        return v

    @field_validator('lon')
    @classmethod
    def validate_lon(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (not math.isfinite(v) or v < -180 or v > 180):
            raise ValueError('Längengrad muss eine endliche Zahl zwischen -180 und 180 sein.')
        return v


class BedUpdateRequest(BaseModel):
    deaktiviert_ab: Optional[date] = None
    is_active: Optional[bool] = None
    valid_from: Optional[date] = None


class LocationSummaryResponse(BaseModel):
    id: UUID
    name: str
    kontingent: int
    notbett_kapazitaet: int
    belegt: int
    belegungsgrad_pct: float
    is_active: bool
    lat: Optional[float] = None
    lon: Optional[float] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Bed Status (für Drilldown-Bettgitter)
# ---------------------------------------------------------------------------


class BedStatusItem(BaseModel):
    bed_id: UUID
    bett_nummer: str
    bett_typ: str
    status: str  # FREI | BELEGT | VORGEMERKT
    # BELEGT: aktueller Belegter
    occupancy_id: Optional[UUID] = None
    azr_id: Optional[str] = None
    alias_id: Optional[str] = None
    occ_geschlecht: Optional[str] = None
    belegung_start: Optional[date] = None
    belegung_ende: Optional[date] = None
    room_labels: list[str] = []
    bed_labels: list[str] = []
    occ_labels: list[str] = []
    deaktiviert_ab: Optional[date] = None
    bed_valid_from: Optional[date] = None
    is_notbett: bool = False
    extended_once: bool = False
    # VORGEMERKT: zugehörige bestätigte Reservierung
    reservation_id: Optional[UUID] = None
    reservation_azr_id: Optional[str] = None
    reservation_start: Optional[date] = None
    reservation_ende: Optional[date] = None
    # Verlegungsstatus
    has_pending_transfer: bool = False        # BELEGT: Verlegungsanfrage läuft (PENDING)
    has_confirmed_transfer: bool = False      # BELEGT: Transfer bestätigt, Ausbuchung ausstehend (CONFIRMED)
    pending_reservation_id: Optional[UUID] = None  # FREI: Bett ist suggested_bed in PENDING-Anfrage
    pending_requester_location_name: Optional[str] = None  # FREI: Name der anfragenden Einrichtung
    outgoing_reservation_id: Optional[UUID] = None  # BELEGT: ID der ausgehenden PENDING/CONFIRMED-Anfrage
    transfer_target_location_name: Optional[str] = None  # BELEGT: Name der Ziel-Einrichtung
    pending_azr_id: Optional[str] = None  # FREI: AZR-ID der anfragenden Person


class RoomBedStatus(BaseModel):
    room_id: UUID
    room_name: str
    geschlechts_designation: str
    room_type: str = "STANDARD"  # STANDARD | WARTEBEREICH
    beds: list[BedStatusItem]
    pending_count: int = 0
    labels: list[str] = []
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


class LabelCatalogEntry(BaseModel):
    name: str
    category: str
    entity_types: list[str]  # ROOM, BED, OCCUPANCY
    color: str


class LabelCatalogResponse(BaseModel):
    items: list[LabelCatalogEntry]


class LabelsUpdateRequest(BaseModel):
    labels: list[str]
