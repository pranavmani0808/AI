from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General Settings
    APP_NAME: str = "AI Search Engine"
    APP_ENV: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # PostgreSQL Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/ai_search"

    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # SearXNG Configuration
    SEARXNG_URL: str = "http://searxng:8080"
    SEARXNG_SECRET_KEY: str = "34293f0b2f3484c2f42a5a9c086d7cb0efb32e652a9261a9b20ad97ee899c75a"

    # Qdrant Configuration
    QDRANT_URL: str = "http://qdrant:6333"

    # LLM Configuration (For Later Phases)
    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"

    # Embedding Configuration (For Later Phases)
    EMBEDDING_PROVIDER: str = "local"

settings = Settings()
