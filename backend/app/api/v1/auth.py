from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.audit import AuditEvent
from app.schemas.user import UserCreate, UserLogin, UserOut, Token, UserProvisionRequest
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.roles import Role
from app.core.exceptions import ConflictException, AppException
from app.api.deps import require_current_user, require_admin_or_above

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_citizen(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Public registration endpoint for citizens.
    Self-registration is restricted strictly to the CITIZEN role.
    """
    existing = await db.execute(select(User).filter(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise ConflictException(f"User with email '{user_in.email}' already exists.")

    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=Role.CITIZEN.value,  # Enforce citizen role for public signup
        assigned_district_id=None,
        assigned_state_id=None,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    audit = AuditEvent(
        actor=new_user.email,
        action="citizen_registered",
        affected_record=f"User:{new_user.id}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/provision", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def provision_officer_or_admin(
    user_in: UserProvisionRequest,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrative provisioning endpoint.
    Only State Administrators and System Administrators can provision officers and admins.
    """
    normalized_role = Role.normalize(user_in.role)
    if current_user.normalized_role == Role.STATE_ADMIN:
        # State admin can only provision district officers within their own state
        if normalized_role not in {Role.DISTRICT_OFFICER}:
            raise HTTPException(
                status_code=403,
                detail="State Administrators can only provision District Officers."
            )
        user_in.assigned_state_id = current_user.assigned_state_id

    existing = await db.execute(select(User).filter(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise ConflictException(f"User with email '{user_in.email}' already exists.")

    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=normalized_role.value,
        assigned_district_id=user_in.assigned_district_id,
        assigned_state_id=user_in.assigned_state_id,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    audit = AuditEvent(
        actor=current_user.email,
        action=f"provision_{normalized_role.value}",
        affected_record=f"User:{new_user.id}",
        details={"role": normalized_role.value, "district": user_in.assigned_district_id, "state": user_in.assigned_state_id},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == credentials.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated",
        )

    token = create_access_token(subject=user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "assigned_district_id": user.assigned_district_id,
        "assigned_state_id": user.assigned_state_id,
    }


@router.get("/me", response_model=UserOut)
async def get_current_user_profile(current_user: User = Depends(require_current_user)):
    return current_user
