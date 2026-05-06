"""
models.py
---------
SQLAlchemy ORM models for Veritas.

Tables
------
  verified_articles  — Cached analysis results, keyed by URL.
  analysis_jobs      — Per-job status tracker for the agentic pipeline.
                       Enables reliable polling and WebSocket push.
"""

import datetime
import uuid
from sqlalchemy import Column, Integer, String, DateTime, Text

from .database import Base


class VerifiedArticle(Base):
    """Stores cached verification results to avoid re-running expensive analysis."""

    __tablename__ = "verified_articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    article_title = Column(String, nullable=True)
    analysis_json = Column(Text, nullable=False)
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)


class AnalysisJob(Base):
    """
    Tracks the lifecycle of each analysis request through the agent pipeline.

    Status transitions:
        pending → running → done | failed
    """

    __tablename__ = "analysis_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), nullable=False, default="pending", index=True)
    input_type = Column(String(10), nullable=False)   # "url" | "file" | "text"
    input_ref = Column(Text, nullable=True)            # URL, filename, or text excerpt
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)