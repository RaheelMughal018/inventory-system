from pydantic_settings import BaseSettings
from pydantic import model_validator
from urllib.parse import quote_plus
import os

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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env" if os.getenv("APP_ENV", "local") == "local" else ".env.prod"
        env_file_encoding = "utf-8"
    
    @model_validator(mode='after')
    def construct_database_url(self):
        """Construct DATABASE_URL from components if not provided directly."""
        if not self.DATABASE_URL:
            if not self.DB_NAME:
                raise ValueError("Either DATABASE_URL or DB_NAME must be provided")
            
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
        