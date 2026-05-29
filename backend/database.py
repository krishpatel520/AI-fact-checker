"""
database.py
-----------
SQLAlchemy engine and session factory.

Requires a PostgreSQL DATABASE_URL — set via environment variable.
Example: postgresql://veritas:veritas@localhost:5432/veritas
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Set it to a PostgreSQL connection string, e.g. "
        "postgresql://veritas:veritas@localhost:5432/veritas"
    )
if not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError(
        f"DATABASE_URL must be a PostgreSQL connection string (got: {DATABASE_URL!r}). "
        "SQLite is not supported."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # detect stale connections
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,    # recycle connections after 1 hour (avoid idle timeouts)
    pool_timeout=30,      # raise after 30s if no connection slot is available
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()