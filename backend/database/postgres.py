from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from backend.core.config import settings

# Create async database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def check_postgres_health() -> bool:
    """Verifies Postgres database connection by executing a simple SELECT 1 query."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        print(f"Postgres health check connection error: {e}")
        return False

async def get_db():
    """Dependency helper to manage database sessions cleanly."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
