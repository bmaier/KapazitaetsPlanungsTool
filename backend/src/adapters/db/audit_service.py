"""Zentraler Audit-Service: einzige Schreibstelle für audit.events."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.models import AuditEventModel
from src.adapters.keycloak.jwt import UserContext


def _highest_role(roles: list[str]) -> Optional[str]:
    for r in ("system-admin", "location-admin", "writer", "reader"):
        if r in roles:
            return r
    return roles[0] if roles else None


async def write_audit(
    session: AsyncSession,
    event_type: str,
    payload: dict,
    user: Optional[UserContext] = None,
    location_id: Optional[UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> None:
    """
    Schreibt einen Audit-Eintrag in audit.events — append-only.
    Gleiche Session wie die aufrufende Mutation → atomares Commit.
    """
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    if user is not None:
        actor_id = user.sub
        actor_role = _highest_role(user.roles)
        if user.username:
            payload = {**payload, "actor_username": user.username}

    loc_uuid: Optional[UUID] = location_id
    if loc_uuid is None and user is not None and user.location_id:
        try:
            loc_uuid = UUID(user.location_id)
        except ValueError:
            pass

    event = AuditEventModel(
        id=uuid4(),
        event_type=event_type,
        payload=payload,
        created_at=datetime.now(timezone.utc),
        actor_id=actor_id,
        actor_role=actor_role,
        location_id=loc_uuid,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.add(event)
