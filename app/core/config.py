from pydantic_settings import BaseSettings
from pydantic import model_validator
from urllib.parse import quote_plus
import os

# Env var names some platforms use for PostgreSQL (checked in order)
_DATABASE_URL_ENV_ALIASES = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "DATABASE_PRIVATE_URL",
    "POSTGRES_CONNECTION_STRING",
    "POSTGRESQL_URL",
)


def _get_database_url_from_env() -> str | None:
    """Get database URL from environment, trying common platform variable names."""
    for name in _DATABASE_URL_ENV_ALIASES:
        value = os.environ.get(name)
        if value and value.strip().startswith("postgres"):
            return value.strip()
    return None


class Settings(BaseSettings):
    APP_ENV: str = "local"
    
    # Database URL - can be provided directly or constructed from components
    DATABASE_URL: str | None = None
    
    # Individual database components (for constructing DATABASE_URL)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = ""
    
    # Other settings
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    class Config:
        env_file = ".env" if os.getenv("APP_ENV", "local") == "local" else ".env.prod"
        env_file_encoding = "utf-8"
    
    @model_validator(mode='after')
    def construct_database_url(self):
        """Construct DATABASE_URL from components or common env vars if not provided directly."""
        if not self.DATABASE_URL:
            # Try common platform env var names (Railway, Render, etc.)
            self.DATABASE_URL = _get_database_url_from_env()
        if not self.DATABASE_URL:
            if not self.DB_NAME:
                raise ValueError(
                    "Either DATABASE_URL or DB_NAME must be provided. "
                    "On Railway: add variable DATABASE_URL = ${{Postgres.DATABASE_URL}}. "
                    "On Render: link the PostgreSQL database to get DATABASE_URL."
                )
            # URL encode password to handle special characters
            password_part = f":{quote_plus(self.DB_PASSWORD)}" if self.DB_PASSWORD else ""
            self.DATABASE_URL = f"postgresql://{self.DB_USER}{password_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
        # Ensure DATABASE_URL is always a string after validation
        assert self.DATABASE_URL is not None, "DATABASE_URL must be set"
        return self
    
    @property
    def database_url(self) -> str:
        """Get DATABASE_URL as a guaranteed string."""
        assert self.DATABASE_URL is not None, "DATABASE_URL must be set"
        return self.DATABASE_URL

settings = Settings()
        