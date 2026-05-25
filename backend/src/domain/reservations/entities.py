"""
Domain-Entities für Reservierungsanfragen.
Reine Python-Datenklassen — kein I/O, kein FastAPI-Import, kein SQLAlchemy-Import.
"""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional
import uuid


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    TRANSFERRED = "TRANSFERRED"


@dataclass
class ReservationRequest:
    id: uuid.UUID
    requester_location_id: uuid.UUID
    target_location_id: uuid.UUID
    azr_id: str
    geschlecht: str
    geburtsjahr: int
    herkunftsland: str
    belegung_start: date
    belegung_ende: date
    status: ReservationStatus
    confirmed_bed_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
