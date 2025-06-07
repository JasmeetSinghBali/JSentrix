"""
gateway/src/core/models/user
Pydantic models for user data validation and type hints.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    employee_number: str


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    roles: str

    class Config:
        from_attributes = True


class UserPublic(UserBase):
    id: int
    roles: str

    class Config:
        from_attributes = True
