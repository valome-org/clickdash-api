from .connection import engine, get_db
from .models import Base, Dashboard


# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

__all__ = ["Base", "engine", "get_db", "Dashboard", "create_tables"]
