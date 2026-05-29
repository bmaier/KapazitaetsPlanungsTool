"""
Domain Value Objects für das Kapazitätsmanagement.
Kein FastAPI-Import, kein SQLAlchemy-Import — reine Domain-Logik.
"""
from enum import Enum


class GenderDesignation(str, Enum):
    M = "M"   # männlich
    W = "W"   # weiblich
    F = "F"   # Familie
    D = "D"   # divers


class BedType(str, Enum):
    KONTINGENT = "KONTINGENT"
    NOTBETT = "NOTBETT"
    DOPPEL = "DOPPEL"
    WARTEPLATZ = "WARTEPLATZ"  # Platz im Wartebereich — zählt nicht gegen Kontingent
