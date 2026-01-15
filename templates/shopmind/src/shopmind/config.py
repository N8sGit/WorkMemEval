"""
Configuration settings for ShopMind.

Uses pydantic-settings to load configuration from environment variables
with sensible defaults for local development.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "ShopMind"
    debug: bool = True

    # Database
    # Default uses SQLite for easy local dev; switch to PostgreSQL for production
    database_url: str = "sqlite:///./shopmind.db"

    # JWT Authentication
    secret_key: str = "dev-secret-key-change-in-production"  # TODO: Generate proper secret
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
