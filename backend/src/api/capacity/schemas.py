"""
Pydantic v2 Request/Response-Schemas für die Kapazitäts-API.
DSGVO: OccupancyCreate hat kein name-Feld — nur azr_id, alias_id, geschlecht, Daten.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    geschlechts_designation: GenderDesignation


class RoomResponse(BaseModel):
    id: UUID
    location_id: UUID
    name: str
    geschlechts_designation: GenderDesignation
    is_active: bool
    labels: list[str] = []

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


class BedUpdateRequest(BaseModel):
    deaktiviert_ab: Optional[date] = None
    is_active: Optional[bool] = None


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

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Bed Status (für Drilldown-Bettgitter)
# ---------------------------------------------------------------------------


class BedStatusItem(BaseModel):
    bed_id: UUID
    bett_nummer: str
    bett_typ: str
    status: str  # FREI | BELEGT | VORGEMERKT
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
    is_notbett: bool = False


class RoomBedStatus(BaseModel):
    room_id: UUID
    room_name: str
    geschlechts_designation: str
    beds: list[BedStatusItem]
    pending_count: int = 0  # Offene Reservierungsanfragen für diesen Raum
    labels: list[str] = []


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
