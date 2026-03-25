from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.config.engine import SessionDep
from src.crud import users_crud
from src.models.users import User, UserAdmin, UserUpdate
from src.security.auth import get_current_user

router = APIRouter()


# === Authenticated as Admin ===
@router.get(
    "/profile/{username}",
    response_model=UserAdmin,
    summary="Get user profile as admin",
    status_code=status.HTTP_200_OK,
)
async def get_user_profile_as_admin(
    username: str,
    session: SessionDep,
):
    # Admin access enforced by the global dependency in app.py.
    """Get user info only visible for admins"""
    user = users_crud.get_user_by_username(username, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserAdmin.model_validate(user)


@router.delete(
    "/delete/{username}",
    summary="Delete user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    username: str,
    session: SessionDep,
    # Admin access enforced by the global dependency in app.py.
    # get_current_user is used here to retrieve the admin object for
    # the self-deletion guard; admin role is already guaranteed.
    current_admin: User = Depends(get_current_user),
):
    """Delete user by username as admin"""
    if current_admin.username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself.",
        )
    user = users_crud.get_user_by_username(username, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    users_crud.delete_user_by_username(username, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/profile/{username}",
    response_model=UserAdmin,
    summary="Update user as admin",
    status_code=status.HTTP_200_OK,
)
async def update_user_as_admin(
    user_update: UserUpdate,
    username: str,
    session: SessionDep,
):
    # Admin access enforced by the global dependency in app.py.
    """Update user by username as admin"""
    user = users_crud.get_user_by_username(username, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user_update.email and user_update.email != user.email:
        existing_email = users_crud.get_user_by_email(user_update.email, session)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )

    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    updated_user = users_crud.update_user(user, session)
    return UserAdmin.model_validate(updated_user)
