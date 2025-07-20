from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    MONGODB_DATABASE: str = Field(default="risk-db", env="MONGODB_DATABASE")   
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="localhost", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

def validate_settings():
    """Validate required settings"""
    errors = []

    if not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY must be provided")

    if not settings.MONGODB_URL:
        errors.append("MONGODB_URL must be provided")

    if not settings.LOG_LEVEL:
        errors.append("LOG_LEVEL must be provided")

    if not settings.HOST:
        errors.append("HOST must be provided")

    if not settings.PORT:
        errors.append("PORT must be provided")

    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")

    return True