from http.client import HTTPException
import os
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from src import app
from src.config.engine import get_session
from src.crud import users_crud
from src.models.users import User, UserCreate, UserRead
from src.security.creds import security

router = APIRouter()


# Endpoints básicos
@router.get("/")
async def read_root():
    return {
        "title": app.title,
        "description": app.description,
        "version": app.version
    }

@router.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join('statics', 'favicon.ico'))

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/register", response_model=UserRead, summary="Register new user")
async def register_user( user_data: UserCreate, session: Session = Depends(get_session),):
    """Registrar nuevo usuario con validaciones"""
    if users_crud.get_user_by_username(user_data.username, session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered")

    if users_crud.get_user_by_email(user_data.email, session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = security.hash_password(user_data.password)
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["password_hash"] = hashed_password

    user = User(**user_dict)
    users_crud.create_user(user, session)
    return UserRead.model_validate(user)