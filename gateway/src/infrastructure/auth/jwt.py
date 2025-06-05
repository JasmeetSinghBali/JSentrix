"""
infrastructure/auth/jwt.py
JWT token creation and decoding utilities using pyjwt.
"""

import jwt
from datetime import datetime, timedelta, timezone
from core.config.settings import settings


def create_access_token(data: dict, expires_delta: int = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode a JWT token and return the payload.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
