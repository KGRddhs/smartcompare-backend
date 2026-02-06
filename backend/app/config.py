"""
SmartCompare Backend - Configuration
Uses pydantic-settings for type-safe config from environment variables
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # --- OpenAI ---
    openai_api_key: str
    
    # --- Serper ---
    serper_api_key: str
    
    # --- Supabase ---
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    
    # --- Upstash Redis ---
    upstash_redis_url: str
    upstash_redis_token: str
    
    # --- App Config ---
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # --- Rate Limiting ---
    free_tier_daily_limit: int = 5
    
    # --- Cost Protection ---
    max_monthly_cost: float = 100.0
    cache_duration: int = 86400  # 24 hours in seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid reading .env file multiple times.
    """
    return Settings()


# Quick access
settings = get_settings()
