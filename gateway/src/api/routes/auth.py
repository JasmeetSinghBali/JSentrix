"""
gateway/src/api/routes
API routes for user authentication and onboarding.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.session import get_db
from core.models.user import UserCreate, UserPublic
from application.use_cases.auth import authenticate_user, create_user
from infrastructure.auth.jwt import create_access_token

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
