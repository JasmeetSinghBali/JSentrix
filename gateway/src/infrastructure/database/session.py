"""
gateway/src/infrastructure/database/session
Database engine and session management for async SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config.settings import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=10,  # Tune as needed
    max_overflow=5,  # Tune as needed
    echo=True,  # 🎈 set to False in production
)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """
    Dependency to provide a new SQLAlchemy session per request.
    """
    async with AsyncSessionLocal() as session:
        yield session
