"""
models.py
---------
SQLAlchemy ORM models for caching verified article results.
"""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from .database import Base


class VerifiedArticle(Base):
    """
    Stores cached verification results to avoid re-running expensive
    analysis for recently seen URLs.
    """
    __tablename__ = "verified_articles"

    id = Column(Integer, primary_key=True, index=True)

    # The source URL – unique, indexed for fast lookups
    url = Column(String, unique=True, index=True, nullable=False)

    # Article headline extracted during analysis
    article_title = Column(String, nullable=True)

    # Full JSON blob of the analysis result
    analysis_json = Column(Text, nullable=False)

    # When the analysis was performed (UTC)
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)