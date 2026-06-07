from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: UUID
    event_type: str
    payload: Optional[Any] = None
    created_at: datetime
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    location_id: Optional[UUID] = None
    location_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


class AuditListResponse(BaseModel):
    items: List[AuditEntryOut]
    total: int
    page: int
    page_size: int
