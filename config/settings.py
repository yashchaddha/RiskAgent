from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "risk-db"
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o"
    
    # Application Configuration
    debug: bool = False
    log_level: str = "INFO"
    
    # Session Configuration
    session_timeout_minutes: int = 60
    max_regeneration_count: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
