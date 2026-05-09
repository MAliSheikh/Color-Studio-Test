"""
database.py — SQLAlchemy engine + session factory.

Uses DATABASE_URL from .env. Defaults to SQLite for local development.
Change DATABASE_URL to a PostgreSQL connection string to use the Task 1 schema.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Default to a local SQLite file inside Task 4 for self-contained development.
# Set DATABASE_URL=postgresql://user:pass@host/db to connect to your Postgres instance.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./task4_reviews.db")

# SQLite connect_args fix (needed for multi-thread Flask dev server)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Yield a database session (for use with dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
