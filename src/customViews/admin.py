# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime, timedelta

from src.config.engine import get_session
from src.utils.funcdb import get_current_admin_user
from src.models.users import User, UserRead, UserUpdate, UserStatus, UserRole

router = APIRouter()

# === DASHBOARD / ESTADÍSTICAS ===

@router.get("/dashboard", summary="Admin Dashboard")
async def admin_dashboard(
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """Dashboard con estadísticas básicas para administradores"""
    
    # Contar usuarios totales
    total_users = session.exec(select(func.count(User.id))).first()
    
    # Usuarios activos
    active_users = session.exec(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
    ).first()
    
    # Usuarios registrados hoy
    today = datetime.now(datetime.UTC).date()
    users_today = session.exec(
        select(func.count(User.id)).where(func.date(User.created_at) == today)
    ).first()
    
    # Usuarios por rol
    admin_count = session.exec(
        select(func.count(User.id)).where(User.role == UserRole.ADMIN)
    ).first()
    
    return {
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "users_today": users_today,
            "admin_users": admin_count
        },
        "timestamp": datetime.now(datetime.UTC).date(),
        "admin": {
            "id": current_admin.id,
            "username": current_admin.username
        }
    }

# === GESTIÓN DE USUARIOS ===

@router.get("/users", response_model=List[UserRead], summary="List All Users")
async def list_all_users(
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    search: Optional[str] = Query(None, description="Search by username or email")
):
    """Listar todos los usuarios con filtros y paginación"""
    
    statement = select(User)
    
    # Aplicar filtros
    if status:
        statement = statement.where(User.status == status)
    
    if role:
        statement = statement.where(User.role == role)
    
    if search:
        statement = statement.where(
            (User.username.contains(search)) | 
            (User.email.contains(search))
        )
    
    # Paginación
    statement = statement.offset(skip).limit(limit)
    
    users = session.exec(statement).all()
    
    return [UserRead.model_validate(user) for user in users]

@router.get("/users/{user_id}", response_model=UserRead, summary="Get User by ID")
async def get_user_by_id(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """Obtener información detallada de un usuario"""
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserRead.model_validate(user)

@router.patch("/users/{user_id}", response_model=UserRead, summary="Update User")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """Actualizar información de un usuario"""
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Actualizar campos
    user_data = user_update.model_dump(exclude_unset=True)
    for field, value in user_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserRead.model_validate(user)

@router.delete("/users/{user_id}", summary="Delete User")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """Eliminar un usuario (soft delete cambiando status)"""
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevenir que admin se borre a sí mismo
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Soft delete
    user.status = UserStatus.INACTIVE
    user.updated_at = datetime.utcnow()
    
    session.add(user)
    session.commit()
    
    return {"message": f"User {user.username} deleted successfully"}

# === GESTIÓN DE ROLES ===

@router.patch("/users/{user_id}/role", summary="Change User Role")
async def change_user_role(
    user_id: int,
    new_role: UserRole,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """Cambiar el rol de un usuario"""
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevenir que admin se quite permisos a sí mismo
    if user.id == current_admin.id and new_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin role from yourself"
        )
    
    old_role = user.role
    user.role = new_role
    user.updated_at = datetime.utcnow()
    
    session.add(user)
    session.commit()
    
    return {
        "message": f"User role changed from {old_role} to {new_role}",
        "user": {
            "id": user.id,
            "username": user.username,
            "old_role": old_role,
            "new_role": new_role
        }
    }

# === ESTADÍSTICAS AVANZADAS ===

@router.get("/stats/users", summary="User Statistics")
async def user_statistics(
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
    days: int = Query(30, ge=1, le=365, description="Days to analyze")
):
    """Estadísticas detalladas de usuarios"""
    
    # Fecha límite
    date_limit = datetime.utcnow() - timedelta(days=days)
    
    # Usuarios registrados en el período
    new_users = session.exec(
        select(func.count(User.id)).where(User.created_at >= date_limit)
    ).first()
    
    # Usuarios por estado
    stats_by_status = {}
    for status in UserStatus:
        count = session.exec(
            select(func.count(User.id)).where(User.status == status)
        ).first()
        stats_by_status[status.value] = count
    
    # Usuarios por rol
    stats_by_role = {}
    for role in UserRole:
        count = session.exec(
            select(func.count(User.id)).where(User.role == role)
        ).first()
        stats_by_role[role.value] = count
    
    return {
        "period_days": days,
        "new_users_in_period": new_users,
        "by_status": stats_by_status,
        "by_role": stats_by_role,
        "generated_at": datetime.utcnow()
    }