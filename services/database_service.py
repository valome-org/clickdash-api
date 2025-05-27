from typing import Optional

from database.models import Dashboard, User
from models.dashboard import DashboardConfig
from sqlalchemy.orm import Session
from utils.serialization import make_json_serializable


class DatabaseService:
    """Service for database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_dashboard(
        self,
        dashboard_id: str,
        dashboard_config: DashboardConfig,
        user: User,
        file_url: Optional[str] = None
    ) -> Dashboard:
        """Create a new dashboard in the database"""

        # Ensure data is JSON serializable
        serializable_config = make_json_serializable(dashboard_config.dict())

        db_dashboard = Dashboard(
            dashboard_id=dashboard_id,
            title=dashboard_config.title,
            charts=serializable_config["charts"],
            insights=dashboard_config.insights,
            summary=dashboard_config.summary,
            key_metrics=serializable_config["key_metrics"],
            file_url=file_url,
            status="ready",
            user_id=user.id
        )

        self.db.add(db_dashboard)
        self.db.commit()
        self.db.refresh(db_dashboard)

        return db_dashboard

    def get_dashboard(self, dashboard_id: str, user: Optional[User] = None) -> Optional[Dashboard]:
        """Get dashboard by ID, optionally filtered by user"""
        query = self.db.query(Dashboard).filter(Dashboard.dashboard_id == dashboard_id)

        if user:
            query = query.filter(Dashboard.user_id == user.id)

        return query.first()

    def get_user_dashboards(self, user: User, limit: int = 100, offset: int = 0):
        """Get all dashboards for a specific user"""
        return (
            self.db.query(Dashboard)
            .filter(Dashboard.user_id == user.id)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_dashboard(
        self,
        dashboard_id: str,
        dashboard_config: DashboardConfig,
        user: User
    ) -> Optional[Dashboard]:
        """Update an existing dashboard (only if user owns it)"""
        db_dashboard = self.get_dashboard(dashboard_id, user)

        if not db_dashboard:
            return None

        # Update fields
        serializable_config = make_json_serializable(dashboard_config.dict())
        db_dashboard.title = dashboard_config.title
        db_dashboard.charts = serializable_config["charts"]
        db_dashboard.insights = dashboard_config.insights
        db_dashboard.summary = dashboard_config.summary
        db_dashboard.key_metrics = serializable_config["key_metrics"]

        self.db.commit()
        self.db.refresh(db_dashboard)

        return db_dashboard

    def delete_dashboard(self, dashboard_id: str, user: User) -> bool:
        """Delete dashboard by ID (only if user owns it)"""
        db_dashboard = self.get_dashboard(dashboard_id, user)

        if not db_dashboard:
            return False

        self.db.delete(db_dashboard)
        self.db.commit()

        return True

    def list_dashboards(self, limit: int = 100, offset: int = 0):
        """List all dashboards with pagination (admin only)"""
        return self.db.query(Dashboard).offset(offset).limit(limit).all()
