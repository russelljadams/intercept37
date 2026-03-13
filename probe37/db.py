"""Database setup and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from probe37.models import Base

DB_PATH = os.environ.get("PROBE37_DB", "probe37_data.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
