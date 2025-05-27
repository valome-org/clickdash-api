from .connection import engine, get_db
from .models import Base, Dashboard, User


# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

__all__ = ["Base", "engine", "get_db", "Dashboard", "User", "create_tables"]
