from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from src.adapters.db.engine import AsyncSessionFactory
from src.config import settings


async def job_12wochen_warnung() -> None:
    async with AsyncSessionFactory() as session:
        try:
            result = await session.execute(text("""
                SELECT DISTINCT r.location_id
                FROM persons.occupants o
                JOIN capacity.beds b ON b.id = o.bed_id
                JOIN capacity.rooms r ON r.id = b.room_id
                JOIN capacity.locations l ON l.id = r.location_id
                WHERE o.belegung_ende BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '84 days'
                  AND l.is_active = true
            """))
            location_ids = [row.location_id for row in result.fetchall()]

            for lid in location_ids:
                existing = await session.execute(text("""
                    SELECT 1 FROM tasks.inbox
                    WHERE location_id = :lid
                      AND task_type = 'WOCHE_12_WARNUNG'
                      AND status = 'OPEN'
                """), {"lid": str(lid)})
                if existing.fetchone():
                    continue
                await session.execute(text("""
                    INSERT INTO tasks.inbox (location_id, task_type, priority, title, body, status)
                    VALUES (:lid, 'WOCHE_12_WARNUNG', 'MEDIUM',
                            '12-Wochen-Näherungswarnung',
                            'Belegungen laufen in ≤12 Wochen ab.',
                            'OPEN')
                """), {"lid": str(lid)})

            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def job_ueberkapazitaet() -> None:
    async with AsyncSessionFactory() as session:
        try:
            result = await session.execute(text("""
                SELECT l.id,
                       l.kontingent + l.notbett_kapazitaet AS kap,
                       COUNT(o.id) AS belegt
                FROM capacity.locations l
                LEFT JOIN capacity.rooms r ON r.location_id = l.id AND r.is_active = true
                LEFT JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true
                LEFT JOIN persons.occupants o ON o.bed_id = b.id
                  AND o.belegung_start <= CURRENT_DATE
                  AND o.belegung_ende > CURRENT_DATE
                WHERE l.is_active = true
                GROUP BY l.id, l.kontingent, l.notbett_kapazitaet
                HAVING COUNT(o.id) > l.kontingent + l.notbett_kapazitaet
            """))
            rows = result.fetchall()

            for row in rows:
                existing = await session.execute(text("""
                    SELECT 1 FROM tasks.inbox
                    WHERE location_id = :lid
                      AND task_type = 'UEBERKAPAZITAET_ALERT'
                      AND status = 'OPEN'
                """), {"lid": str(row.id)})
                if existing.fetchone():
                    continue
                await session.execute(text("""
                    INSERT INTO tasks.inbox (location_id, task_type, priority, title, body, status)
                    VALUES (:lid, 'UEBERKAPAZITAET_ALERT', 'HIGH',
                            'Überkapazität festgestellt',
                            :body,
                            'OPEN')
                """), {
                    "lid": str(row.id),
                    "body": f"Belegte Betten: {row.belegt} / Kapazität: {row.kap}",
                })

            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def job_belegungsbericht() -> None:
    async with AsyncSessionFactory() as session:
        try:
            result = await session.execute(text("""
                SELECT l.id, l.name,
                       l.kontingent + l.notbett_kapazitaet AS kap,
                       COUNT(o.id) AS belegt
                FROM capacity.locations l
                LEFT JOIN capacity.rooms r ON r.location_id = l.id AND r.is_active = true
                LEFT JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true
                LEFT JOIN persons.occupants o ON o.bed_id = b.id
                  AND o.belegung_start <= CURRENT_DATE
                  AND o.belegung_ende > CURRENT_DATE
                WHERE l.is_active = true
                GROUP BY l.id, l.name, l.kontingent, l.notbett_kapazitaet
            """))
            rows = result.fetchall()

            for row in rows:
                existing = await session.execute(text("""
                    SELECT 1 FROM tasks.inbox
                    WHERE location_id = :lid
                      AND task_type = 'KAPAZITAET_BERICHT'
                      AND status = 'OPEN'
                """), {"lid": str(row.id)})
                if existing.fetchone():
                    continue
                kap = int(row.kap or 0)
                belegt = int(row.belegt or 0)
                pct = belegt * 100 // kap if kap else 0
                await session.execute(text("""
                    INSERT INTO tasks.inbox (location_id, task_type, priority, title, body, status)
                    VALUES (:lid, 'KAPAZITAET_BERICHT', 'LOW',
                            'Wöchentlicher Kapazitätsbericht',
                            :body,
                            'OPEN')
                """), {
                    "lid": str(row.id),
                    "body": f"Auslastung: {belegt}/{kap} ({pct}%)",
                })

            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def job_cleanup() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.task_cleanup_days)
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("""
                DELETE FROM tasks.inbox
                WHERE status IN ('DONE', 'DISMISSED')
                  AND updated_at < :cutoff
            """), {"cutoff": cutoff})
            await session.commit()
        except Exception:
            await session.rollback()
            raise
