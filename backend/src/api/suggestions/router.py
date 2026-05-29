import json
import uuid
from collections import defaultdict
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

# ---------------------------------------------------------------------------
# Core SQL: available beds for a given gender and period
# Includes location validity date check.
# ---------------------------------------------------------------------------

_BED_SELECT = """
    SELECT b.id, b.bett_nummer, b.bett_typ,
           r.name AS room_name, r.labels AS room_labels,
           l.name AS location_name, l.id AS location_id
    FROM capacity.beds b
    JOIN capacity.rooms r ON r.id = b.room_id
    JOIN capacity.locations l ON l.id = r.location_id
    WHERE r.is_active = true
      AND b.is_active = true
      AND b.bett_typ != 'NOTBETT'
      AND b.bett_typ != 'DOPPEL'
      AND r.room_type != 'WARTEBEREICH'
      AND (b.deaktiviert_ab IS NULL OR b.deaktiviert_ab > :period_start)
      AND (l.valid_from IS NULL OR l.valid_from <= :period_start)
      AND (l.valid_until IS NULL OR l.valid_until > :period_start)
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

# Variants without gender filter (ignore_gender=True)
_BED_SELECT_NO_GENDER = """
    SELECT b.id, b.bett_nummer, b.bett_typ,
           r.name AS room_name, r.labels AS room_labels,
           l.name AS location_name, l.id AS location_id
    FROM capacity.beds b
    JOIN capacity.rooms r ON r.id = b.room_id
    JOIN capacity.locations l ON l.id = r.location_id
    WHERE r.is_active = true
      AND b.is_active = true
      AND b.bett_typ != 'NOTBETT'
      AND b.bett_typ != 'DOPPEL'
      AND r.room_type != 'WARTEBEREICH'
      AND (b.deaktiviert_ab IS NULL OR b.deaktiviert_ab > :period_start)
      AND (l.valid_from IS NULL OR l.valid_from <= :period_start)
      AND (l.valid_until IS NULL OR l.valid_until > :period_start)
      AND NOT EXISTS (
        SELECT 1 FROM persons.occupants o
        WHERE o.bed_id = b.id
          AND o.belegung_start < :period_end
          AND o.belegung_ende > :period_start
      )
"""

SQL_SCOPED_NO_GENDER = _BED_SELECT_NO_GENDER + """
      AND r.location_id = :loc_id
    ORDER BY r.name, b.bett_nummer
"""

SQL_CROSS_NO_GENDER = _BED_SELECT_NO_GENDER + """
      AND l.is_active = true
    ORDER BY l.name, r.name, b.bett_nummer
"""


# ---------------------------------------------------------------------------
# Helper: fetch available beds for a gender
# ---------------------------------------------------------------------------


async def _fetch_beds(session, geschlecht: str, body: SuggestionRequest, loc_id=None) -> list[BedOption]:
    if body.ignore_gender:
        sql = SQL_SCOPED_NO_GENDER if loc_id else SQL_CROSS_NO_GENDER
        params: dict = {
            "period_start": body.belegung_start,
            "period_end": body.belegung_ende,
        }
    else:
        sql = SQL_SCOPED if loc_id else SQL_CROSS
        params = {
            "geschlecht": geschlecht,
            "period_start": body.belegung_start,
            "period_end": body.belegung_ende,
        }
    if loc_id:
        params["loc_id"] = str(loc_id)
    result = await session.execute(text(sql), params)
    rows = result.fetchall()
    beds = [
        BedOption(
            bed_id=str(r.id),
            bett_nummer=r.bett_nummer,
            room_name=r.room_name,
            bett_typ=r.bett_typ,
            location_name=r.location_name,
            location_id=str(r.location_id),
            room_labels=list(r.room_labels or []),
        )
        for r in rows
    ]
    if body.label_filter:
        beds = [b for b in beds if all(lbl in b.room_labels for lbl in body.label_filter)]
    return beds


# ---------------------------------------------------------------------------
# Variant computation helpers
# ---------------------------------------------------------------------------


def _same_beds(a: list[BedOption], b: list[BedOption]) -> bool:
    return {x.bed_id for x in a} == {x.bed_id for x in b}


def _greedy_pick(beds: list[BedOption], count: int) -> list[BedOption]:
    """Pick `count` beds, preferring fewest rooms (greedy fill by room size desc)."""
    by_room: dict[str, list[BedOption]] = defaultdict(list)
    for b in beds:
        by_room[b.room_name].append(b)
    selected: list[BedOption] = []
    for room_beds in sorted(by_room.values(), key=lambda x: -len(x)):
        selected.extend(room_beds)
        if len(selected) >= count:
            return selected[:count]
    return selected


def _best_variants_for_loc(
    beds: list[BedOption], anzahl: int, loc_name: str, loc_id: str, is_own: bool, max_variants: int = 2
) -> list[Variant]:
    """Generate up to `max_variants` Variants for a single location."""
    if not beds:
        return []

    # Single person: every free bed is its own selectable option
    if anzahl == 1:
        sorted_beds = sorted(beds, key=lambda b: (b.room_name, b.bett_nummer))
        return [
            Variant(beds=[b], location_name=loc_name, is_own=is_own, description=b.room_name)
            for b in sorted_beds[:max_variants]
        ]

    by_room: dict[str, list[BedOption]] = defaultdict(list)
    for b in beds:
        by_room[b.room_name].append(b)

    found: list[list[BedOption]] = []

    # Option 1: single room with enough beds
    for room_beds in sorted(by_room.values(), key=lambda x: -len(x)):
        if len(room_beds) >= anzahl:
            found.append(room_beds[:anzahl])
            if len(found) >= max_variants:
                break

    # Option 2: greedy fill (if different from above)
    if len(found) < max_variants and len(beds) >= anzahl:
        greedy = _greedy_pick(beds, anzahl)
        if len(greedy) >= anzahl and not any(_same_beds(greedy, f) for f in found):
            found.append(greedy)

    if not found and beds:
        # Partial: fewer beds than requested
        partial = beds[:anzahl]
        found.append(partial)

    variants = []
    for bed_list in found[:max_variants]:
        rooms_in_variant = len({b.room_name for b in bed_list})
        desc = f"1 Raum" if rooms_in_variant == 1 else f"{rooms_in_variant} Räume"
        if len(bed_list) < anzahl:
            desc = f"Nur {len(bed_list)} von {anzahl} Plätzen"
        variants.append(Variant(
            beds=bed_list,
            location_name=loc_name,
            is_own=is_own,
            description=desc,
        ))
    return variants


def _compute_cross_location_variants(
    available: list[BedOption], anzahl: int, own_loc_id: str
) -> tuple[list[Variant], str]:
    """Per-location variants: own first (up to 2), then each other location."""
    by_loc: dict[str, list[BedOption]] = defaultdict(list)
    loc_id_map: dict[str, str] = {}
    for b in available:
        by_loc[b.location_name].append(b)
        loc_id_map[b.location_name] = b.location_id

    variants: list[Variant] = []

    # Determine own location name
    own_loc_name = next((name for name, lid in loc_id_map.items() if lid == own_loc_id), None)

    # Own location first — for single person show all free beds, otherwise up to 2 variants
    if own_loc_name and own_loc_name in by_loc:
        max_own = len(by_loc[own_loc_name]) if anzahl == 1 else 2
        own_vars = _best_variants_for_loc(
            by_loc[own_loc_name], anzahl, own_loc_name, own_loc_id, is_own=True, max_variants=max_own
        )
        variants.extend(own_vars)

    # Other locations, sorted by available bed count descending
    others = sorted(
        [(name, beds) for name, beds in by_loc.items() if name != own_loc_name],
        key=lambda x: -len(x[1])
    )
    for loc_name, loc_beds in others:
        loc_id = loc_id_map[loc_name]
        # For single person: show all free beds per location; otherwise 1 greedy variant
        max_other = len(loc_beds) if anzahl == 1 else 1
        v_list = _best_variants_for_loc(loc_beds, anzahl, loc_name, loc_id, is_own=False, max_variants=max_other)
        variants.extend(v_list)

    message = ''
    if not variants:
        message = "Keine freien Plätze verfügbar."
    elif not any(len(v.beds) >= anzahl for v in variants):
        message = f"Kein Standort hat {anzahl} freie Plätze. Standortübergreifende Zuteilung erforderlich."

    return variants, message


def _compute_local_variants(available: list[BedOption], anzahl: int, loc_name: str, loc_id: str) -> tuple[list[Variant], str]:
    """Variants for own location only."""
    if len(available) < anzahl:
        return [], f"Nur {len(available)} Plätze verfügbar. Nicht genug in dieser Einrichtung."
    # For single person: show every free bed; otherwise up to 3 greedy variants
    max_v = len(available) if anzahl == 1 else 3
    variants = _best_variants_for_loc(available, anzahl, loc_name, loc_id, is_own=True, max_variants=max_v)
    return variants, ''


# ---------------------------------------------------------------------------
# Multi-gender group variants
# ---------------------------------------------------------------------------


def _compute_multi_gender_variants(
    avail_m: list[BedOption], count_m: int,
    avail_w: list[BedOption], count_w: int,
    avail_d: list[BedOption], count_d: int,
    own_loc_id: str,
    cross_location: bool,
) -> tuple[list[Variant], str]:
    """Variants for groups with mixed genders (M+W+D counts)."""
    by_loc_m: dict[str, list[BedOption]] = defaultdict(list)
    by_loc_w: dict[str, list[BedOption]] = defaultdict(list)
    by_loc_d: dict[str, list[BedOption]] = defaultdict(list)
    loc_id_map: dict[str, str] = {}

    for b in avail_m:
        by_loc_m[b.location_name].append(b)
        loc_id_map[b.location_name] = b.location_id
    for b in avail_w:
        by_loc_w[b.location_name].append(b)
        loc_id_map[b.location_name] = b.location_id
    for b in avail_d:
        by_loc_d[b.location_name].append(b)
        loc_id_map[b.location_name] = b.location_id

    all_locs = set(loc_id_map.keys())
    own_loc_name = next((n for n, lid in loc_id_map.items() if lid == own_loc_id), None)

    def try_loc(loc_name: str) -> Variant | None:
        m_beds = by_loc_m.get(loc_name, [])
        w_beds = by_loc_w.get(loc_name, [])
        d_beds = by_loc_d.get(loc_name, [])
        if len(m_beds) < count_m or len(w_beds) < count_w or len(d_beds) < count_d:
            return None
        beds: list[BedOption] = []
        if count_m > 0:
            beds.extend(_greedy_pick(m_beds, count_m))
        if count_w > 0:
            beds.extend(_greedy_pick(w_beds, count_w))
        if count_d > 0:
            beds.extend(_greedy_pick(d_beds, count_d))
        parts = []
        if count_m > 0:
            parts.append(f"{count_m}M")
        if count_w > 0:
            parts.append(f"{count_w}W")
        if count_d > 0:
            parts.append(f"{count_d}D")
        return Variant(
            beds=beds,
            location_name=loc_name,
            is_own=(loc_name == own_loc_name),
            description=" + ".join(parts),
        )

    variants: list[Variant] = []

    # Own location first
    if own_loc_name:
        v = try_loc(own_loc_name)
        if v:
            variants.append(v)

    # Other locations
    if cross_location:
        for loc_name in sorted(all_locs - {own_loc_name}, key=lambda n: -(
            len(by_loc_m.get(n, [])) + len(by_loc_w.get(n, [])) + len(by_loc_d.get(n, []))
        )):
            v = try_loc(loc_name)
            if v:
                variants.append(v)

    needs = []
    if count_m > 0:
        needs.append(f"{count_m} Männer")
    if count_w > 0:
        needs.append(f"{count_w} Frauen")
    if count_d > 0:
        needs.append(f"{count_d} Divers")

    message = '' if variants else f"Kein Standort hat freie Plätze für {' + '.join(needs)}"
    return variants, message


# ---------------------------------------------------------------------------
# Family variants
# ---------------------------------------------------------------------------


def _compute_family_variants(
    avail_d: list[BedOption],
    avail_m: list[BedOption],
    avail_w: list[BedOption],
    body: SuggestionRequest,
    own_loc_id: str,
) -> tuple[list[Variant], str]:
    """
    Family placement:
    1. All in one family/D room (best option)
    2. M adults in M room + (W adults + children) in W/D room (gender-split)
    """
    total = body.anzahl
    erw_m = body.maenner_anzahl
    erw_w = body.frauen_anzahl
    kinder = body.minderjaehrige

    by_room_d: dict[tuple[str, str], list[BedOption]] = defaultdict(list)
    for b in avail_d:
        by_room_d[(b.location_name, b.room_name)].append(b)

    by_loc_d: dict[str, list[BedOption]] = defaultdict(list)
    for b in avail_d:
        by_loc_d[b.location_name].append(b)

    by_loc_m: dict[str, list[BedOption]] = defaultdict(list)
    for b in avail_m:
        by_loc_m[b.location_name].append(b)

    by_loc_w: dict[str, list[BedOption]] = defaultdict(list)
    for b in avail_w:
        by_loc_w[b.location_name].append(b)

    loc_id_map: dict[str, str] = {}
    for b in avail_d + avail_m + avail_w:
        loc_id_map[b.location_name] = b.location_id

    own_loc_name = next((n for n, lid in loc_id_map.items() if lid == own_loc_id), None)

    variants: list[Variant] = []

    # --- Option 1: single family room ---
    def family_room_for_loc(loc_name: str) -> Variant | None:
        for (lname, rname), room_beds in by_room_d.items():
            if lname == loc_name and len(room_beds) >= total:
                return Variant(
                    beds=room_beds[:total],
                    location_name=loc_name,
                    is_own=(loc_name == own_loc_name),
                    description=f"Familienraum: {total} Personen in einem Raum",
                )
        return None

    # Own location family room first
    if own_loc_name:
        v = family_room_for_loc(own_loc_name)
        if v:
            variants.append(v)

    # Other locations family rooms
    for loc_name in sorted(set(b.location_name for b in avail_d) - {own_loc_name}):
        v = family_room_for_loc(loc_name)
        if v:
            variants.append(v)

    # --- Option 2: gender-split (M adults separate from W adults+children) ---
    if erw_m > 0 and (erw_w + kinder) > 0:
        all_locs = set(loc_id_map.keys())

        def gender_split_for_loc(loc_name: str) -> Variant | None:
            m_beds = by_loc_m.get(loc_name, [])
            w_beds = by_loc_w.get(loc_name, []) + by_loc_d.get(loc_name, [])
            if len(m_beds) < erw_m or len(w_beds) < (erw_w + kinder):
                return None
            m_sel = _greedy_pick(m_beds, erw_m)
            w_sel = _greedy_pick(w_beds, erw_w + kinder)
            return Variant(
                beds=m_sel + w_sel,
                location_name=loc_name,
                is_own=(loc_name == own_loc_name),
                description=f"Geschlechtertrennung: {erw_m}M + {erw_w + kinder}W/Kinder",
            )

        if own_loc_name:
            v = gender_split_for_loc(own_loc_name)
            if v and not any(_same_beds(v.beds, vv.beds) for vv in variants):
                variants.append(v)

        for loc_name in sorted(all_locs - {own_loc_name}):
            v = gender_split_for_loc(loc_name)
            if v and not any(_same_beds(v.beds, vv.beds) for vv in variants):
                variants.append(v)

    message = '' if variants else f"Kein Raum für {total} Personen verfügbar."
    return variants, message


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------


@router.post("/suggestions", response_model=SuggestionResponse)
async def create_suggestion(
    body: SuggestionRequest,
    location=Depends(get_location_context),
):
    own_loc_id = str(location.id)
    is_multi_gender = body.maenner_anzahl + body.frauen_anzahl + body.divers_anzahl > 0

    async with AsyncSessionFactory() as session:
        if body.familien_modus:
            loc_id_arg = None if body.cross_location else location.id
            avail_d = await _fetch_beds(session, 'D', body, loc_id_arg)
            avail_m = await _fetch_beds(session, 'M', body, loc_id_arg) if body.maenner_anzahl > 0 else []
            avail_w = await _fetch_beds(session, 'W', body, loc_id_arg) if body.frauen_anzahl > 0 else []
            variants, message = _compute_family_variants(avail_d, avail_m, avail_w, body, own_loc_id)

        elif is_multi_gender:
            loc_id_arg = None if body.cross_location else location.id
            avail_m = await _fetch_beds(session, 'M', body, loc_id_arg) if body.maenner_anzahl > 0 else []
            avail_w = await _fetch_beds(session, 'W', body, loc_id_arg) if body.frauen_anzahl > 0 else []
            avail_d = await _fetch_beds(session, 'D', body, loc_id_arg) if body.divers_anzahl > 0 else []
            variants, message = _compute_multi_gender_variants(
                avail_m, body.maenner_anzahl,
                avail_w, body.frauen_anzahl,
                avail_d, body.divers_anzahl,
                own_loc_id,
                body.cross_location,
            )

        else:
            # Single gender
            loc_id_arg = None if body.cross_location else location.id
            available = await _fetch_beds(session, body.geschlecht, body, loc_id_arg)

            if body.cross_location:
                variants, message = _compute_cross_location_variants(available, body.anzahl, own_loc_id)
            else:
                # Local only: determine own location name
                own_name = ''
                if available:
                    own_name = available[0].location_name  # all from same loc
                variants, message = _compute_local_variants(available, body.anzahl, own_name, own_loc_id)

        event_id = str(uuid.uuid4())
        audit_payload = json.dumps({
            "location_id": own_loc_id,
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
