"""
Keycloak JWT-Validation für FastAPI.
Dependency get_current_user prüft Bearer-Token gegen JWKS-Endpoint.
JWKS wird in-memory gecacht (TTL 5 Minuten).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import LocationModel
from src.config import settings


@dataclass
class UserContext:
    sub: str
    roles: list[str] = field(default_factory=list)
    location_id: Optional[str] = None


_jwks_cache: Optional[dict] = None
_jwks_fetched_at: Optional[datetime] = None
_JWKS_TTL_SECONDS = 300

_READER_PLUS = frozenset({"reader", "writer", "location-admin", "system-admin"})
_WRITER_PLUS = frozenset({"writer", "location-admin", "system-admin"})


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = datetime.now(timezone.utc)
    if (
        _jwks_cache is not None
        and _jwks_fetched_at is not None
        and (now - _jwks_fetched_at).total_seconds() < _JWKS_TTL_SECONDS
    ):
        return _jwks_cache
    jwks_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/certs"
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_fetched_at = now
    return _jwks_cache


async def get_current_user(request: Request) -> UserContext:
    """FastAPI Dependency: validiert Bearer-Token. HTTP 401 bei ungültigem/fehlendem Token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header[len("Bearer "):]
    public_base = settings.keycloak_public_url or settings.keycloak_url
    expected_issuer = f"{public_base}/realms/{settings.keycloak_realm}"
    try:
        jwks = await _fetch_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        if payload.get("iss") != expected_issuer:
            raise HTTPException(status_code=401, detail="Not authenticated")
        sub = payload.get("sub", "")
        roles = payload.get("realm_access", {}).get("roles", [])
        loc_id = payload.get("location_id")
        user_roles = set(roles)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not (user_roles & _WRITER_PLUS):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        elif not (user_roles & _READER_PLUS):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return UserContext(sub=sub, roles=roles, location_id=loc_id)
    except HTTPException:
        raise
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Not authenticated")


async def _get_db_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


async def get_location_context(
    x_location_id: Optional[UUID] = Header(None),
    session: AsyncSession = Depends(_get_db_session),
    user: UserContext = Depends(get_current_user),
) -> LocationModel:
    """
    FastAPI Dependency: liest X-Location-Id-Header, fällt auf JWT-Claim zurück.
    HTTP 403 wenn weder Header noch Claim vorhanden, oder Location nicht aktiv.
    """
    loc_uuid: Optional[UUID] = x_location_id
    if loc_uuid is None and user.location_id:
        try:
            loc_uuid = UUID(user.location_id)
        except ValueError:
            pass
    if loc_uuid is None:
        raise HTTPException(status_code=403, detail="Keine Einrichtung im Token oder Header")
    result = await session.execute(
        select(LocationModel).where(LocationModel.id == loc_uuid)
    )
    loc = result.scalar_one_or_none()
    if not loc or not loc.is_active:
        raise HTTPException(status_code=403, detail="Location nicht gefunden oder inaktiv")
    return loc
