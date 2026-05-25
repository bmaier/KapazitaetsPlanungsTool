import json
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.keycloak.jwt import get_location_context
from src.api.suggestions.schemas import (
    AcceptRequest,
    BedOption,
    RejectRequest,
    SuggestionRequest,
    SuggestionResponse,
    Variant,
)

router = APIRouter(tags=["suggestions"])

_BED_SELECT = """
    SELECT b.id, b.bett_nummer, b.bett_typ, r.name AS room_name, l.name AS location_name,
           r.labels AS room_labels
    FROM capacity.beds b
    JOIN capacity.rooms r ON r.id = b.room_id
    JOIN capacity.locations l ON l.id = r.location_id
    WHERE r.is_active = true
      AND b.is_active = true
      AND b.bett_typ != 'NOTBETT'
      AND (b.deaktiviert_ab IS NULL OR b.deaktiviert_ab > :period_start)
      AND NOT EXISTS (
        SELECT 1 FROM persons.occupants o
        WHERE o.bed_id = b.id
          AND o.belegung_start < :period_end
          AND o.belegung_ende > :period_start
      )
      AND (
        /* 1. Explicit gender label on room matches request */
        (:geschlecht = 'M' AND 'Männer' = ANY(r.labels))
        OR (:geschlecht = 'W' AND 'Frauen' = ANY(r.labels))
        OR (:geschlecht = 'D' AND ('Familie' = ANY(r.labels) OR 'Familienraum' = ANY(r.labels) OR 'Gemischt' = ANY(r.labels)))
        /* 2. Room has no gender label - check current occupants */
        OR (
          NOT ('Männer' = ANY(r.labels) OR 'Frauen' = ANY(r.labels) OR 'Familie' = ANY(r.labels) OR 'Familienraum' = ANY(r.labels) OR 'Gemischt' = ANY(r.labels))
          AND (
            /* Empty room: any gender welcome */
            NOT EXISTS (
              SELECT 1 FROM persons.occupants o2
              JOIN capacity.beds b2 ON b2.id = o2.bed_id
              WHERE b2.room_id = r.id
                AND o2.belegung_start < :period_end
                AND o2.belegung_ende > :period_start
            )
            /* Or room has occupants of same gender */
            OR EXISTS (
              SELECT 1 FROM persons.occupants o3
              JOIN capacity.beds b3 ON b3.id = o3.bed_id
              WHERE b3.room_id = r.id
                AND o3.geschlecht = :geschlecht
                AND o3.belegung_start < :period_end
                AND o3.belegung_ende > :period_start
            )
            /* Divers requests can go anywhere without gender labels */
            OR :geschlecht = 'D'
          )
        )
        /* 3. Keep backward compat: old geschlechts_designation */
        OR r.geschlechts_designation = 'D'
      )
"""

SQL_SCOPED = _BED_SELECT + """
      AND r.location_id = :loc_id
    ORDER BY r.name, b.bett_nummer
"""

SQL_CROSS = _BED_SELECT + """
      AND l.is_active = true
    ORDER BY l.name, r.name, b.bett_nummer
"""


@router.post("/suggestions", response_model=SuggestionResponse)
async def create_suggestion(
    body: SuggestionRequest,
    location=Depends(get_location_context),
):
    async with AsyncSessionFactory() as session:
        sql = SQL_CROSS if body.cross_location else SQL_SCOPED
        params = {
            "geschlecht": body.geschlecht,
            "period_start": body.belegung_start,
            "period_end": body.belegung_ende,
        }
        if not body.cross_location:
            params["loc_id"] = str(location.id)

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        available = [
            BedOption(
                bed_id=str(r.id),
                bett_nummer=r.bett_nummer,
                room_name=r.room_name,
                bett_typ=r.bett_typ,
                location_name=r.location_name,
                room_labels=list(r.room_labels or []),
            )
            for r in rows
        ]

        # Apply label filter: room must have ALL required labels
        if body.label_filter:
            available = [
                b for b in available
                if all(lbl in (b.room_labels or []) for lbl in body.label_filter)
            ]

        message = ''
        if body.familien_modus and body.minderjaehrige > 0:
            variants, message = _compute_family_variants(available, body.anzahl)
        elif len(available) < body.anzahl:
            if not body.cross_location:
                message = (
                    f"Nur {len(available)} Betten verfügbar. "
                    "Nicht genug Plätze in dieser Einrichtung. Standortübergreifende Suche empfohlen."
                )
            else:
                message = f"Nur {len(available)} Betten verfügbar"
            variants = []
        else:
            variants = _compute_variants(available, body.anzahl)
            if not body.cross_location and len(variants) > 0 and not any(
                len(v.beds) >= body.anzahl for v in variants
            ):
                message = (
                    "Nicht genug Plätze in dieser Einrichtung. "
                    "Standortübergreifende Suche empfohlen."
                )

        event_id = str(uuid.uuid4())
        audit_payload = json.dumps({
            "location_id": str(location.id),
            "geschlecht": body.geschlecht,
            "anzahl": body.anzahl,
            "belegung_start": str(body.belegung_start),
            "belegung_ende": str(body.belegung_ende),
            "variants_count": len(variants),
            "cross_location": body.cross_location,
            "familien_modus": body.familien_modus,
        })
        await session.execute(
            text(
                "INSERT INTO audit.events (id, event_type, payload) "
                "VALUES (:event_id, 'SUGGESTION_CREATED', :audit_payload)"
            ),
            {"event_id": event_id, "audit_payload": audit_payload},
        )
        await session.commit()

    return SuggestionResponse(suggestion_id=event_id, variants=variants, message=message)


def _compute_family_variants(beds: list[BedOption], anzahl: int) -> tuple[list[Variant], str]:
    from collections import defaultdict
    by_room: dict[tuple[str, str], list[BedOption]] = defaultdict(list)
    for b in beds:
        by_room[(b.location_name, b.room_name)].append(b)

    for room_beds in by_room.values():
        if len(room_beds) >= anzahl:
            return [Variant(beds=room_beds[:anzahl])], ''

    return [], f"Kein Raum für {anzahl} Personen zusammen verfügbar"


def _compute_variants(beds: list[BedOption], anzahl: int) -> list[Variant]:
    from collections import defaultdict
    by_room: dict[tuple[str, str], list[BedOption]] = defaultdict(list)
    for b in beds:
        by_room[(b.location_name, b.room_name)].append(b)

    variants: list[list[BedOption]] = []

    # Variant 1: single room with enough beds
    for room_beds in by_room.values():
        if len(room_beds) >= anzahl:
            variants.append(room_beds[:anzahl])
            break

    # Variant 2: fewest rooms (greedy fill)
    greedy: list[BedOption] = []
    for room_beds in sorted(by_room.values(), key=lambda x: -len(x)):
        greedy.extend(room_beds)
        if len(greedy) >= anzahl:
            greedy = greedy[:anzahl]
            break
    if greedy and not any(_same_beds(greedy, v) for v in variants):
        variants.append(greedy)

    # Variant 3: first N beds alphabetically (already sorted)
    first_n = beds[:anzahl]
    if not any(_same_beds(first_n, v) for v in variants):
        variants.append(first_n)

    return [Variant(beds=v) for v in variants[:3]]


def _same_beds(a: list[BedOption], b: list[BedOption]) -> bool:
    return {x.bed_id for x in a} == {x.bed_id for x in b}


def _load_created_event(row) -> dict:
    payload = row.payload
    return payload if isinstance(payload, dict) else json.loads(payload)


@router.post("/suggestions/{suggestion_id}/accept", status_code=200)
async def accept_suggestion(
    suggestion_id: UUID,
    body: AcceptRequest,
    location=Depends(get_location_context),
):
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("""
            SELECT id, payload FROM audit.events
            WHERE id = :sid AND event_type = 'SUGGESTION_CREATED'
        """), {"sid": str(suggestion_id)})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden")
        payload_data = _load_created_event(row)
        if payload_data.get("location_id") != str(location.id):
            raise HTTPException(status_code=403, detail="Zugriff verweigert")
        variants_count = payload_data.get("variants_count", 0)
        if body.variant_index >= variants_count:
            raise HTTPException(
                status_code=422,
                detail=f"variant_index muss < {variants_count} sein",
            )
        await session.execute(
            text(
                "INSERT INTO audit.events (event_type, payload) "
                "VALUES ('SUGGESTION_ACCEPTED', :payload)"
            ),
            {"payload": json.dumps({
                "suggestion_id": str(suggestion_id),
                "variant_index": body.variant_index,
                "location_id": str(location.id),
            })},
        )
        await session.commit()
    return {"status": "accepted"}


@router.post("/suggestions/{suggestion_id}/reject", status_code=200)
async def reject_suggestion(
    suggestion_id: UUID,
    body: RejectRequest,
    location=Depends(get_location_context),
):
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("""
            SELECT id, payload FROM audit.events
            WHERE id = :sid AND event_type = 'SUGGESTION_CREATED'
        """), {"sid": str(suggestion_id)})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden")
        payload_data = _load_created_event(row)
        if payload_data.get("location_id") != str(location.id):
            raise HTTPException(status_code=403, detail="Zugriff verweigert")
        await session.execute(
            text(
                "INSERT INTO audit.events (event_type, payload) "
                "VALUES ('SUGGESTION_REJECTED', :payload)"
            ),
            {"payload": json.dumps({
                "suggestion_id": str(suggestion_id),
                "reason": body.reason,
                "location_id": str(location.id),
            })},
        )
        await session.commit()
    return {"status": "rejected"}
