from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import datetime, timezone

from src.config.engine import get_session
from src.crud import users_crud
from src.models.users import User, UserRead, UserUpdate
from src.security.auth import get_current_user


router = APIRouter()

# === Authenticated ===
@router.get("/me", response_model=UserRead, summary="Get current user")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return UserRead.model_validate(current_user)

@router.patch("/me", response_model=UserUpdate, summary="Update current user")
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update current authenticated user info"""
    if user_update.email and user_update.email != current_user.email:
        existing_email = users_crud.get_user_by_email(email=user_update.email, session=session)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.now(timezone.utc)
    return users_crud.update_user(user=current_user, session=session)