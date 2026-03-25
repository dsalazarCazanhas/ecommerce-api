import os

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError

from src.config.engine import SessionDep
from src.crud import users_crud
from src.models.users import User, UserCreate, UserRead
from src.security.creds import security

router = APIRouter()


# === Public Endpoints ===
@router.get("/", status_code=status.HTTP_200_OK)
async def read_root(request: Request):
    return {
        "title": request.app.title,
        "description": request.app.description,
        "version": request.app.version,
    }


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join("statics", "favicon.ico"))


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}


@router.post(
    "/register",
    response_model=UserRead,
    summary="Register new user",
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: UserCreate,
    session: SessionDep,
):
    """Register a new user"""
    if users_crud.get_user_by_username(user_data.username, session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if users_crud.get_user_by_email(user_data.email, session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = security.hash_password(user_data.password)
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["password_hash"] = hashed_password

    user = User(**user_dict)
    try:
        users_crud.create_user(user, session)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )

    return UserRead.model_validate(user)
