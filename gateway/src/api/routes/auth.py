"""
gateway/src/api/routes/auth
API routes for user authentication and onboarding.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.session import get_db
from core.models.user import UserCreate, UserPublic
from application.use_cases.auth import authenticate_user, create_user
from infrastructure.auth.jwt import create_access_token
from api.dependencies import get_current_user

router = APIRouter()


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint for obtaining JWT access token.
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/onboard", response_model=UserPublic)
async def onboard_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Onboard a new user.
    """
    db_user = await create_user(user_data, db)
    return db_user


@router.get("/me", response_model=UserPublic)
async def read_current_user(current_user: UserPublic = Depends(get_current_user)):
    """
    Get details of the currently authenticated user.
    Accessible to any authenticated user (admin, auditor, etc).
    """
    return current_user
