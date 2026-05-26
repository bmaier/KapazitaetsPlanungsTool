from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class SuggestionRequest(BaseModel):
    geschlecht: Literal['M', 'W', 'D'] = 'M'
    anzahl: int = Field(ge=1, le=200, default=1)
    belegung_start: date
    belegung_ende: date
    cross_location: bool = False
    familien_modus: bool = False
    minderjaehrige: int = Field(default=0, ge=0)
    label_filter: list[str] = []
    include_notbetten: bool = False
    # Multi-gender group / family split
    maenner_anzahl: int = Field(default=0, ge=0)
    frauen_anzahl: int = Field(default=0, ge=0)
    divers_anzahl: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def check_dates_and_family(self):
        if self.belegung_ende <= self.belegung_start:
            raise ValueError("belegung_ende muss nach belegung_start liegen")
        if self.familien_modus and self.minderjaehrige == 0:
            raise ValueError("familien_modus erfordert mindestens einen Minderjährigen (minderjaehrige >= 1)")
        if self.familien_modus and self.minderjaehrige >= self.anzahl:
            raise ValueError("mindestens eine erwachsene Person erforderlich")
        return self


class BedOption(BaseModel):
    bed_id: str
    bett_nummer: str
    room_name: str
    bett_typ: str
    location_name: str = ''
    location_id: str = ''
    room_labels: list[str] = []


class Variant(BaseModel):
    beds: list[BedOption]
    location_name: str = ''
    is_own: bool = False
    description: str = ''


class SuggestionResponse(BaseModel):
    suggestion_id: str
    variants: list[Variant]
    message: str = ''


class AcceptRequest(BaseModel):
    variant_index: int = Field(ge=0)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
