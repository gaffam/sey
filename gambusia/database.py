from contextlib import asynccontextmanager
from datetime import datetime

from .config import settings

from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_id = Column(String, nullable=False)
    temp = Column(Float)
    humidity = Column(Float)
    freq = Column(Integer)
    image_verified = Column(Boolean)
    lat = Column(Float)
    lon = Column(Float)
    extra_sensors = Column(JSON)


async def init_db() -> None:
    """Create database tables if they do not exist.

    Note
    ----
    This helper is intended for development only. In production deployments
    migrations managed by a tool such as Alembic should be used instead of
    calling ``create_all`` directly.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Yield an async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        finally:
            await session.close()
