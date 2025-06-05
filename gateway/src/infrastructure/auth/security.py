"""
gateway/src/infrastructure/auth
Password hashing and verification using bcrypt.
"""

import bcrypt


def get_password_hash(password: str) -> str:
    """
    Hash a plain password for storage using bcrypt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
