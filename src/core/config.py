from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application configuration"""
    
    # App Info
    app_name: str = "TruthShield API"
    version: str = "0.1.0"
    debug: bool = True
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./truthshield.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Social Media APIs
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_bearer_token: str = ""
    
    # AI APIs
    openai_api_key: str = ""
    huggingface_api_key: str = ""
    
    # Security
    secret_key: str = "your-secret-key-change-this"
    jwt_secret: str = "your-jwt-secret-change-this"
    
    # German Companies to Monitor
    default_companies: List[str] = ["vodafone", "bmw", "bayer", "deutsche_telekom"]
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()