from pydantic import UUID4
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime
import uuid


"""
Los UUIDs previenen la filtración de información.
Debido a que los UUIDs versión 4 son aleatorios, puedes asignar estos IDs a los usuarios de la aplicación o a otros sistemas sin exponer información sobre tu aplicación.

Al usar enteros auto-incrementales como claves primarias, podrías exponer implícitamente información sobre tu sistema.
Por ejemplo, alguien podría crear un nuevo héroe y, al obtener el ID de héroe 20, sabría que tienes 20 héroes en tu sistema (o incluso menos, si algunos héroes ya fueron eliminados).

Aún existe una pequeña posibilidad de colisión, pero es muy baja.
En la mayoría de los casos puedes asumir que no ocurrirá, pero sería bueno estar preparado para ello.
"""
class BaseModel(SQLModel):
    """Modelo base con campos comunes"""
    id: UUID4 = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    class Config:
        from_attributes = True
