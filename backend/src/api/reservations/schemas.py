"""
Pydantic-Schemas für die Reservierungs-API.
DSGVO-Minimalprofil: azr_id, geschlecht, geburtsjahr, herkunftsland — kein Name, kein Foto.
"""
from datetime import date, datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReservationCreate(BaseModel):
    target_location_id: uuid.UUID
    azr_id: str = Field(max_length=50)
    geschlecht: str = Field(max_length=10)
    geburtsjahr: int
    herkunftsland: str  # ISO 3166-1 alpha-3 (3 Zeichen)
    belegung_start: date
    belegung_ende: date

    @field_validator("geburtsjahr")
    @classmethod
    def validate_geburtsjahr(cls, v: int) -> int:
        import datetime as _dt
        current_year = _dt.date.today().year
        if v <= 1900 or v > current_year:
            raise ValueError(f"geburtsjahr muss zwischen 1901 und {current_year} liegen")
        return v

    @field_validator("herkunftsland")
    @classmethod
    def validate_herkunftsland(cls, v: str) -> str:
        if len(v) != 3 or not v.isalpha():
            raise ValueError("herkunftsland muss ein ISO 3166-1 alpha-3 Code sein (genau 3 Buchstaben)")
        return v.upper()

    @model_validator(mode="after")
    def ende_after_start(self):
        if self.belegung_ende <= self.belegung_start:
            raise ValueError("belegung_ende muss nach belegung_start liegen")
        return self


class ReservationResponse(BaseModel):
    id: uuid.UUID
    requester_location_id: uuid.UUID
    target_location_id: uuid.UUID
    azr_id: str
    geschlecht: str
    geburtsjahr: int
    herkunftsland: str
    belegung_start: date
    belegung_ende: date
    status: str
    confirmed_bed_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
