"""
Datenbank-Health-Check-Adapter.
Prüft die Erreichbarkeit der PostgreSQL-Datenbank.
"""
from sqlalchemy import text

from src.adapters.db.engine import engine


async def check_db_health() -> bool:
    """
    Führt eine minimale DB-Abfrage aus, um die Verbindung zu prüfen.
    Gibt True zurück wenn die DB erreichbar ist, sonst False.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
