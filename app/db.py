# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import DATABASE_URL

Base = declarative_base()

# DATABASE_URL мисалы: postgresql+asyncpg://user:pass@host:5432/db
ENGINE = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = async_sessionmaker(
    bind=ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
)
