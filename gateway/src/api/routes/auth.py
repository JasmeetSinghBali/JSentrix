"""
gateway/src/api/routes/auth
API routes for user authentication and onboarding.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.session import get_db
from core.models.user import UserCreate, UserPublic
from application.use_cases.auth import authenticate_user, create_user
from application.services.logger import logger
from infrastructure.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from api.dependencies import get_current_user, get_active_user_by_email

router = APIRouter()


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint for obtaining JWT access and refresh token.
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # check admin ban
    if getattr(user, "admin_ban", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been banned by an administrator.",
        )
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Contact admin.",
        )
    # 📌 never set is_active = True here
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# 🎈 though this route has no actual functional-op
@router.post("/logout", summary="Logout user by clearing client credentials")
async def logout():
    """
    Logout endpoint for stateless JWT:
    - On the client side, remove access/refresh tokens.
    - 📌 pure statelessness, don’t implement server-side blacklists/revocations—log out by having the client simply delete the token).
    """
    return {"message": "Logged out successfully"}


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


@router.post("/refresh", summary="Get new access and refresh token using refresh token")
async def refresh_access_token(
    refresh_token: str = Body(..., embed=True), db: AsyncSession = Depends(get_db)
):
    """
    Exchange a valid refresh token for a new access and refresh token.
    """
    import jwt

    try:
        payload = decode_access_token(refresh_token)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # dependency for user lookup and activity check
    user = await get_active_user_by_email(email, db)
    if user:
        logger.info(f"USER-look-up: {user}")

    access_token = create_access_token(data={"sub": email})
    new_refresh_token = create_refresh_token(data={"sub": email})
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
