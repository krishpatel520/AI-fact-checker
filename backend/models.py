import datetime
from sqlalchemy import Column, Integer, String, DateTime
from .database import Base

class VerifiedArticle(Base):
    """
    Database model for storing cached verification results.
    """
    __tablename__ = "verified_articles"

    id = Column(Integer, primary_key=True, index=True)
    
    # The URL of the article, must be unique. Indexed for fast lookups.
    url = Column(String, unique=True, index=True, nullable=False)
    
    # The full JSON analysis result will be stored as a string.
    analysis_json = Column(String, nullable=False)
    
    # The timestamp when the analysis was performed.
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)