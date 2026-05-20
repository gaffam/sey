from contextlib import asynccontextmanager
from datetime import datetime, timezone

from .config import settings

from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
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
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    device_id = Column(String, nullable=False)
    temp = Column(Float)
    humidity = Column(Float)
    freq = Column(Integer)
    image_verified = Column(Boolean)
    lat = Column(Float)
    lon = Column(Float)
    extra_sensors = Column(JSON)
    risk_score = Column(Float)
    pesticide_risk = Column(Float)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        finally:
            await session.close()
