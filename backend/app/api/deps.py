from typing import Optional, List, Set, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_token
from app.core.roles import Role
from app.core.exceptions import (
    PermissionDeniedException,
    DistrictAccessDeniedException,
    AppException,
)
from app.db.session import get_db
from app.models.user import User
from app.models.geography import District

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).filter(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_current_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: Union[Role, str]):
    """Parametric dependency factory checking user has one of the allowed roles."""
    normalized_allowed = {Role.normalize(r) for r in allowed_roles}

    async def role_checker(user: User = Depends(require_current_user)) -> User:
        user_role = user.normalized_role
        if user_role not in normalized_allowed:
            raise PermissionDeniedException(
                f"Role '{user.role}' is not authorized. Required one of: {[r.value for r in normalized_allowed]}"
            )
        return user

    return role_checker


# Role shortcut dependencies
require_citizen = require_role(Role.CITIZEN)
require_district_officer = require_role(Role.DISTRICT_OFFICER)
require_state_admin = require_role(Role.STATE_ADMIN)
require_system_admin = require_role(Role.SYSTEM_ADMIN)
require_officer_or_above = require_role(Role.DISTRICT_OFFICER, Role.STATE_ADMIN, Role.SYSTEM_ADMIN)
require_admin_or_above = require_role(Role.STATE_ADMIN, Role.SYSTEM_ADMIN)


async def verify_district_jurisdiction(
    user: User,
    district_id: int,
    db: AsyncSession,
) -> bool:
    """
    Enforces geographic jurisdiction rules at the backend level.
    - SYSTEM_ADMIN: Global jurisdiction.
    - STATE_ADMIN: Any district within user's assigned state.
    - DISTRICT_OFFICER: ONLY user's assigned district.
    - CITIZEN: Access denied.
    """
    user_role = user.normalized_role

    if user_role == Role.SYSTEM_ADMIN:
        return True

    if user_role == Role.STATE_ADMIN:
        if not user.assigned_state_id:
            raise PermissionDeniedException("State Administrator account is not assigned to any state.")
        # Check if district belongs to this state
        res = await db.execute(select(District).filter(District.id == district_id))
        dist = res.scalar_one_or_none()
        if not dist or dist.state_id != user.assigned_state_id:
            raise DistrictAccessDeniedException(
                officer_district_id=None,
                requested_district_id=district_id,
            )
        return True

    if user_role == Role.DISTRICT_OFFICER:
        if user.assigned_district_id != district_id:
            raise DistrictAccessDeniedException(
                officer_district_id=user.assigned_district_id,
                requested_district_id=district_id,
            )
        return True

    raise PermissionDeniedException("Citizens do not have administrative district jurisdiction.")
