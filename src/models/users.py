from sqlmodel import Field
from pydantic import EmailStr
from src.models.base import IdTable


class User(IdTable, table=True):
    """
    Represents a user in the system.
    """
    username: str = Field(nullable=False, max_length=15, index=True, min_length=4, unique=True, description="Unique username for the user.")
    password: str = Field(nullable=False, min_length=8, description="Password for the user account.")
    name: str = Field(nullable=False, max_length=30, description="First name of the user.")
    last_name: str = Field(nullable=False, max_length=30, description="Last name of the user.")
    email: EmailStr = Field(nullable=False, index=True, unique=True, description="Email address of the user.")
    phone: str = Field(nullable=False, max_length=20, description="Phone number of the user.")