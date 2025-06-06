"""
gateway/src/api/dependencies
Reusable FastAPI dependencies for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.session import get_db
from core.config.settings import settings
from core.models.user import UserInDB
from infrastructure.database.models import User
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserInDB:
    """
    Dependency to get the current authenticated user from the JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return UserInDB.from_orm(user)


def require_roles(*roles):
    """
    Dependency factory to require a user to have at least one of the specified roles.
    Usage: Depends(require_roles("superadmin"))
    """

    async def _require_roles(current_user: UserInDB = Depends(get_current_user)):
        user_roles = [role.strip().lower() for role in current_user.roles.split(",")]
        required_roles = [role.strip().lower() for role in roles]
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return _require_roles


async def get_active_user_by_email(
    email: str, db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get an active user by email from the database.
    Raises 401 if user not found or inactive.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user
