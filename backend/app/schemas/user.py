from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.core.roles import Role


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = Role.CITIZEN.value
    assigned_district_id: Optional[int] = None
    assigned_state_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserProvisionRequest(UserBase):
    """Admin-only provisioning request for officers and administrators."""
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    assigned_district_id: Optional[int] = None
    assigned_state_id: Optional[int] = None
