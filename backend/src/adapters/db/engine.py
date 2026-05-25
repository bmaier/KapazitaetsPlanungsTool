"""
SQLAlchemy AsyncEngine und SessionFactory.
Adapter-Schicht: Kein direkter DB-Zugriff in main.py oder Domain-Code.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # Verbindungen werden vor Nutzung geprüft
    pool_size=5,
    max_overflow=10,
)

AsyncSessionFactory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
