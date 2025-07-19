from .connection import engine, get_db
from .models import Base, Dashboard, User, MetadataElement
from .workflow_models import (
    Workflow, DataSource, DataProcessingJob, DataValidation,
    DataCleanup, Approval, DashboardVersion, ExportJob, Notification
)


# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

__all__ = [
    "Base", "engine", "get_db",
    "Dashboard", "User", "MetadataElement",
    "Workflow", "DataSource", "DataProcessingJob", "DataValidation",
    "DataCleanup", "Approval", "DashboardVersion", "ExportJob", "Notification",
    "create_tables"
]
