from pydantic import UUID4
from sqlmodel import Field, SQLModel
import uuid


"""
UUIDs Prevent Information Leakage
Because UUIDs version 4 are random, you could give these IDs to the application users or to other systems, 
without exposing information about your application.

When using auto-incremented integers for primary keys, you could implicitly expose information about your system.
For example, someone could create a new hero, and by getting the hero ID 20 they would know that you have 
20 heroes in your system (or even less, if some heroes were already deleted).

There's still a chance you could have a collision, but it's very low. 
In most cases you could assume you wouldn't have it, but it would be good to be prepared for it.
"""
class IdTable(SQLModel):
    """
    Base table class that provides a UUID primary key field.
    """
    id: UUID4 = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False, unique=True)
