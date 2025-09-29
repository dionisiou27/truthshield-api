from pydantic_settings import BaseSettings
from typing import List, Optional

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
    
    # AI APIs - Diese werden von Environment Variables geladen
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None  # NEU
    news_api_key: Optional[str] = None    # NEU
    
    # Security
    secret_key: str = "your-secret-key-change-this"
    jwt_secret: str = "your-jwt-secret-change-this"
    
    # German Companies to Monitor
    default_companies: List[str] = ["vodafone", "bmw", "bayer", "deutsche_telekom"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Erlaubt GOOGLE_API_KEY oder google_api_key

# Global settings instance
settings = Settings()