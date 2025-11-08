# src/models/base.py
from pydantic import UUID4
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
import uuid


"""
UUIDs prevent information leakage.
Because version 4 UUIDs are random, you can assign these IDs to application users or other systems without exposing information about your application.

When using auto-incrementing integers as primary keys, you could implicitly expose information about your system.

There is still a small possibility of collision, but it is very low.
In most cases you can assume it won't happen, but it would be good to be prepared for it.
"""
class BaseModel(SQLModel, table = False):
    """Base Model"""
    id: Optional[UUID4] = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

