import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load variables from the .env file
load_dotenv()

# --- Read the database URL from the environment, with a default fallback ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./verified_articles.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()