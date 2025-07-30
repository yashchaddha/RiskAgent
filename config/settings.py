import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    app_name: str = Field(default="Risk Management Agent", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="localhost", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Database
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    database_name: str = Field(default="risk-db", env="DATABASE_NAME")
    
    # OpenAI/ChatGPT
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    
    # LangGraph
    langgraph_checkpointer: str = Field(default="memory", env="LANGGRAPH_CHECKPOINTER")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", env="OPENAI_SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24 hours
    
    # CORS
    cors_origins: list = Field(default=["http://localhost:3000", "http://localhost:8000"], env="CORS_ORIGINS")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()