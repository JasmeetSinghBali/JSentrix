"""
gateway/src/core/config/settings
Configuration management using Pydantic BaseSettings for environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field


class Settings(BaseSettings):
    """
    Application settings loaded from .env file or environment variables.
    """

    # Database
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")

    # Auth & Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440, env="REFRESH_TOKEN_EXPIRE_MINUTES"
    )

    # First Superuser
    FIRST_SUPERUSER_EMAIL: str = Field(..., env="FIRST_SUPERUSER_EMAIL")
    FIRST_SUPERUSER_PASSWORD: str = Field(..., env="FIRST_SUPERUSER_PASSWORD")
    FIRST_SUPERUSER_EMPLOYEE_NUMBER: str = Field(
        ..., env="FIRST_SUPERUSER_EMPLOYEE_NUMBER"
    )

    # MCP Server
    MCP_SERVER_HOST: str = Field(default="localhost", env="MCP_SERVER_HOST")
    MCP_SERVER_PORT: int = Field(default=9000, env="MCP_SERVER_PORT")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE_MAX_SIZE_MB: int = Field(default=10, env="LOG_FILE_MAX_SIZE_MB")
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # CORS
    CORS_ALLOW_ORIGINS: str = Field(
        default="http://localhost:3000", env="CORS_ALLOW_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
