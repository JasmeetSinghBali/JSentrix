"""
gateway/src/infrastructure/database/models.py
SQLAlchemy models for persistent entities.
"""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """
    User table for authentication and RBAC.
    """

    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    employee_number = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    admin_ban = Column(
        Boolean, default=False
    )  # 📌 Only a superadmin (via a secure admin panel or endpoint) can set/unset this field.
    is_superuser = Column(Boolean, default=False)
    roles = Column(String, default="user")
