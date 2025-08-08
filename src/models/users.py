# app/models/user.py
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, field_validator, UUID4
from typing import Optional
from enum import Enum
from datetime import datetime
from src.models.base import BaseModel  # Tu IdTable adaptado

class UserRole(str, Enum):
    """Roles disponibles para usuarios"""
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"

class UserStatus(str, Enum):
    """Estados del usuario"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    SUSPENDED = "suspended"

# === SCHEMAS BASE ===

class UserBase(SQLModel):
    """Campos base compartidos - SOLO para validación, no para DB"""
    name: str = Field(min_length=2, max_length=30)
    last_name: str = Field(min_length=2, max_length=30)
    phone: str = Field(min_length=10, max_length=20, regex="^[\+]?[1-9][\d]{3,14}$")
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    username: str = Field(
        min_length=4,
        max_length=15,
        regex="^[a-zA-Z0-9_]+$",
        description="Unique username for the user."
    )
    email: EmailStr = Field(description="Email address of the user.")

    @field_validator('name', 'last_name')
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validar y formatear nombres"""
        if not v.replace(' ', '').replace('-', '').isalpha():
            raise ValueError('Name must contain only letters, spaces and hyphens')
        return v.strip().title()

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validar username"""
        forbidden = ['admin', 'root', 'system', 'api', 'null', 'undefined']
        if v.lower() in forbidden:
            raise ValueError('Username not allowed')
        return v.lower()

# === MODELO DE BASE DE DATOS ===

class User(BaseModel, UserBase, table=True):
    """
    Modelo de usuario para la base de datos.
    Hereda campos de UserBase + configuración específica de DB
    """
    __tablename__ = "users"
    
    # Override campos que necesitan configuración especial de DB
    username: str = Field(
        min_length=4,
        max_length=15,
        index=True,
        unique=True,
        regex="^[a-zA-Z0-9_]+$",
        description="Unique username for the user."
    )
    
    email: EmailStr = Field(
        index=True,
        unique=True,
        description="Email address of the user."
    )
    
    password_hash: str = Field(description="Hashed password")
    
    # Campos adicionales específicos de la DB
    last_login: Optional[datetime] = Field(default=None)
    failed_login_attempts: int = Field(default=0)

# === SCHEMAS PARA API ===

class UserCreate(UserBase):
    """Schema para crear un usuario nuevo - NO hereda de User (table)"""
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Password for the user account (will be hashed)"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validar fortaleza de la contraseña"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserRead(UserBase):
    """Schema para leer usuario (sin información sensible)"""
    id: UUID4  # O UUID si usas UUID en BaseModel
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Permite crear desde objetos SQLModel

class UserUpdate(SQLModel):
    """Schema para actualizar usuario (todos los campos opcionales)"""
    name: Optional[str] = Field(None, min_length=2, max_length=30)
    last_name: Optional[str] = Field(None, min_length=2, max_length=30)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    status: Optional[UserStatus] = None
    
    @field_validator('name', 'last_name')
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.replace(' ', '').replace('-', '').isalpha():
            raise ValueError('Name must contain only letters, spaces and hyphens')
        return v.strip().title()

class UserLogin(SQLModel):
    """Schema para login"""
    username: str = Field(description="username")
    password: str = Field(min_length=1, description="User password")

class UserResponse(SQLModel):
    """Schema para respuestas de login exitoso"""
    user: UserRead
    token_type: str = "bearer"

# === SCHEMAS ADICIONALES ===

class UserPublic(SQLModel):
    """Schema para información pública del usuario (perfiles, comentarios, etc.)"""
    id: int
    username: str
    name: str
    last_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserAdmin(UserRead):
    """Schema con información adicional para administradores"""
    failed_login_attempts: int
    password_hash: str  # Solo para admins
    
    class Config:
        from_attributes = True