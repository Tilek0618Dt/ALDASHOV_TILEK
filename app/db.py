from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import DATABASE_URL

# DATABASE_URL example:
# postgresql+asyncpg://user:pass@host:5432/dbname
ENGINE = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=ENGINE, expire_on_commit=False
)
