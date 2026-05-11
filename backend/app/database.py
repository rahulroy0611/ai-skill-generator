import os
from datetime import datetime
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

load_dotenv()

Base = declarative_base()


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    skill_type = Column(String(50), nullable=False)
    skill_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SkillArtifact(Base):
    __tablename__ = "skill_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float), nullable=True)


class SkillResponse(BaseModel):
    id: int
    name: str
    skill_type: str
    metadata: Optional[dict]
    created_at: str


class UploadResponse(BaseModel):
    skill_id: int
    name: str
    status: str


class QueryResponse(BaseModel):
    answer: str
    sources: Optional[list] = None


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/pdftoskill")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)