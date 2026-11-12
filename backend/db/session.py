"""SQLAlchemy database engine, session factory, and declarative base."""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.core.config import settings

# If using local SQLite file, ensure the parent directory exists
if settings.DATABASE_URL.startswith("sqlite"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path and not db_path.startswith(":memory:"):
        parent_dir = Path(db_path).resolve().parent
        parent_dir.mkdir(parents=True, exist_ok=True)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Keep production/test logs clean
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a clean database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
