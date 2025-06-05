from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    database_url: str
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    first_superuser_email: str
    first_superuser_password: str
    first_superuser_employee_number: str

    class Config:
        env_file = ".env"


settings = Settings()
