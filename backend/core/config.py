import os
from pydantic_settings import BaseSettings, SettingsConfigDict

current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "../../.env"))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_path,
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

    # LLM Configuration
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # RAG Grounding Configurations
    RAG_TOP_K: int = 8
    RAG_MIN_SCORE: float = 0.35
    RAG_MAX_CONTEXT_CHUNKS: int = 6
    RAG_MAX_CONTEXT_CHARS: int = 18000


    # Embedding Configuration
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    QDRANT_COLLECTION: str = "web_evidence"

    # Phase 5 - Multi-Step Research Configurations
    RESEARCH_MAX_ITERATIONS: int = 3
    RESEARCH_MAX_SUBQUERIES: int = 6
    RESEARCH_MAX_SOURCES: int = 20
    RESEARCH_MAX_PARALLEL_SEARCHES: int = 3
    RESEARCH_TIMEOUT_SECONDS: int = 90
    RESEARCH_COVERAGE_THRESHOLD: float = 0.85
    MAX_SOURCES_PER_DOMAIN: int = 2
    WEIGHT_AUTHORITY: float = 0.45
    WEIGHT_RELEVANCE: float = 0.40
    WEIGHT_FRESHNESS: float = 0.15


    # Explicit service timeouts (seconds)
    TIMEOUT_SEARXNG: float = 10.0
    TIMEOUT_QDRANT: float = 10.0
    TIMEOUT_GEMINI: float = 20.0
    TIMEOUT_CRAWLER: float = 10.0
    TIMEOUT_DATABASE: float = 10.0
    
    # Request Size Limits
    MAX_QUERY_LENGTH: int = 4000
    FOLLOWUP_MIN_SIMILARITY: float = 0.70

settings = Settings()
