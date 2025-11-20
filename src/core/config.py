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
    claimbuster_api_key: Optional[str] = None  # NEW
    claimbuster_api_key: Optional[str] = None  # NEU
    
    # Social Media APIs
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-change-this"
    jwt_secret: str = "your-jwt-secret-change-this"
    
    # TikTok Config (optional)
    tiktok_username: Optional[str] = None
    tiktok_password: Optional[str] = None
    
    # Monitoring (optional)
    sentry_dsn: Optional[str] = None
    
    # Development
    debug: bool = True
    environment: str = "development"
    
    # Prioritization thresholds (Reach-first / Risk-first)
    track_pool_min_views: int = 5000
    track_pool_min_growth_rate_24h: float = 0.30  # 30%
    account_pool_min_followers: int = 10000
    account_pool_min_follower_spike_24h: float = 2.0  # 200%
    coordination_min_score: float = 0.5  # 0..1 proxy

    # Astro-Score routing thresholds
    astro_alert_threshold: float = 8.0
    astro_semi_threshold: float = 5.0

    # Virality (0–10) threshold for pre-filter
    virality_threshold: float = 6.0

    # QA sampling
    qa_sample_rate: float = 0.1  # 10% of eligible items
    qa_low_score_threshold: float = 5.0
    qa_high_spread_projected_reach: int = 20000

    # Edge automation (auto-post)
    auto_post_enabled: bool = False

    # Transparency & Legal
    transparency_required: bool = True
    transparency_label_en: str = "This content was generated with AI assistance."
    transparency_label_de: str = "Dieser Inhalt wurde mit KI-Unterstützung erstellt."
    ownership_model_default: str = "client"  # client | truthshield | cobrand
    dpa_contact_email: str = "legal@truthshield.eu"

    # German Companies to Monitor
    default_companies: List[str] = ["vodafone", "bmw", "bayer", "deutsche_telekom"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Erlaubt GOOGLE_API_KEY oder google_api_key
        extra = "ignore"  # Ignoriere zusätzliche Felder in .env

# Global settings instance
settings = Settings()