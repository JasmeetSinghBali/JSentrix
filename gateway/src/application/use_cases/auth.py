"""
gateway/src/application/use_cases
Authentication use cases for user onboarding and login
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from infrastructure.database.models import User
from core.models.user import UserCreate, UserInDB
from infrastructure.auth.security import verify_password, get_password_hash


async def authenticate_user(email: str, password: str, db: AsyncSession):
    """
    Authenticate user credentials
    """
    result = await db.execute(select(User).where(User.email == email))
    # .scalars iterable for scaler values and retrieving the first user object from the result list iterable
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return UserInDB.from_orm(user)


async def create_user(user_data: UserCreate, db: AsyncSession):
    """
    Create a new user in database
    """
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        employee_number=user_data.employee_number,
        is_active=True,
        is_superuser=False,
        roles="user",
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_first_superuser(db: AsyncSession, settings):
    """
    Ensure the first superuser exists on startup.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
    )
    user = result.scalars().first()
    if not user:
        db_user = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Superuser",
            employee_number=settings.FIRST_SUPERUSER_EMPLOYEE_NUMBER,
            is_active=True,
            is_superuser=True,
            roles="superuser,admin",
        )
        db.add(db_user)
        await db.commit()
