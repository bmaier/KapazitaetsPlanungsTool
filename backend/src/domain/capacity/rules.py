"""
Domain-Regeln für das Kapazitätsmanagement.
Reine Funktionen — kein I/O, kein FastAPI-Import, kein SQLAlchemy-Import.
"""
from datetime import date
from typing import Any, Optional

from src.domain.capacity.value_objects import BedType


class DomainError(Exception):
    """Fachlicher Fehler aus der Domain-Schicht. Wird im Router zu HTTP 422."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def check_notbett_duration(bett_typ: BedType, start: date, ende: date) -> None:
    """
    Raises DomainError wenn ein Notbett länger als 1 Nacht belegt wird.
    Notbett erlaubt maximal start + 1 Tag == ende.
    """
    if bett_typ == BedType.NOTBETT and (ende - start).days > 1:
        raise DomainError("Notbett: max. 1 Nacht erlaubt")


def check_12_weeks(start: date, ende: date) -> bool:
    """
    Gibt True zurück wenn die Belegungsdauer 12 Wochen (84 Tage) überschreitet.
    Erzeugt KEINEN Fehler — nur eine Warnung (Response-Header X-12W-Warning).
    """
    return (ende - start).days > 84


def check_eu_quota(
    current_kontingent_sum: int,
    new_kontingent: int,
    eu_gesamtquote: int,
) -> None:
    """
    Raises DomainError wenn die Summe aller Location-Kontingente die
    EU-Gesamtquote überschreiten würde.
    """
    if current_kontingent_sum + new_kontingent > eu_gesamtquote:
        raise DomainError(
            f"EU-Gesamtquote würde überschritten "
            f"({current_kontingent_sum + new_kontingent} > {eu_gesamtquote})"
        )


def check_bed_available(existing_occupancy: Optional[Any]) -> None:
    """
    Raises DomainError wenn das Bett bereits belegt ist.
    existing_occupancy ist None wenn das Bett frei ist.
    """
    if existing_occupancy is not None:
        raise DomainError("Bett bereits belegt")
