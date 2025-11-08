# src/models/users.py
from sqlmodel import Relationship, SQLModel, Field
from pydantic import EmailStr, field_validator, UUID4
from typing import List, Optional
from enum import Enum
from datetime import datetime

from src.models.base import BaseModel


# === SCHEMAS BASE ===
class UserRole(str, Enum):
    """User Roles"""
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"

class UserStatus(str, Enum):
    """User statuses"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    SUSPENDED = "suspended"

class UserBase(SQLModel, table = False):
    """Base fields for validation only"""
    name: str = Field(min_length=2, max_length=30)
    last_name: str = Field(min_length=2, max_length=30)
    phone: str = Field(min_length=10, max_length=20, regex="^[+]?[1-9][0-9]{3,14}$")
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
        """Validate and format names"""
        if not v.replace(' ', '').replace('-', '').isalpha():
            raise ValueError('Name must contain only letters, spaces and hyphens')
        return v.strip().title()

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username against forbidden names"""
        forbidden = ['admin', 'root', 'system', 'api', 'null', 'undefined']
        if v.lower() in forbidden:
            raise ValueError('Username not allowed')
        return v.lower()


# === DB MODEL ===
class User(BaseModel, UserBase, table=True):
    """
    user model for the database
    """
    __tablename__ = "user"
    
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
    
    last_login: Optional[datetime] = Field(default=None)
    failed_login_attempts: int = Field(default=0)

    cart: List["Cart"] = Relationship(back_populates="user") # type: ignore


# === SCHEMAS PARA API ===
class UserCreate(UserBase, table = False):
    """Schema for creating a user"""
    password: str = Field(
        min_length=8,
        max_length=100,
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserRead(UserBase, table = False):
    """Schema for reading user info"""
    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserUpdate(SQLModel, table = False):
    """Schema for updating user info"""
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

class UserLogin(SQLModel, table = False):
    """Schema for user login"""
    username: str = Field(description="username")
    password: str = Field(min_length=1, description="User password")


# === SCHEMAS ADICIONALES ===
class UserAdmin(UserRead, table = False):
    """Schema for admin view of user"""
    id: UUID4
    username: str
    name: str
    last_name: str
    failed_login_attempts: int
    password_hash: str
    
    class Config:
        from_attributes = True