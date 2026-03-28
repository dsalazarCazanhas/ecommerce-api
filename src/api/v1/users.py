from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.config.engine import SessionDep
from src.crud import users_crud
from src.models.users import User, UserRead, UserUpdate
from src.security.auth import get_current_user

users_router = APIRouter()


# === Authenticated ===
@users_router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user",
    status_code=status.HTTP_200_OK,
)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return UserRead.model_validate(current_user)


@users_router.patch(
    "/me",
    response_model=UserRead,
    summary="Update current user",
    status_code=status.HTTP_200_OK,
)
async def update_current_user(
    user_update: UserUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update current authenticated user info"""
    if user_update.email and user_update.email != current_user.email:
        existing_email = users_crud.get_user_by_email(
            email=user_update.email, session=session
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )

    # Regular users can update profile data but not account status.
    for field, value in user_update.model_dump(
        exclude_unset=True,
        exclude={"status"},
    ).items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.now(timezone.utc)
    updated_user = users_crud.update_user(user=current_user, session=session)
    return UserRead.model_validate(updated_user)
