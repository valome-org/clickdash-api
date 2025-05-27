from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    charts = Column(JSON, nullable=False)
    insights = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    key_metrics = Column(JSON, nullable=True)
    status = Column(String, default="ready", nullable=False)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching the current API response"""
        return {
            "dashboard_id": self.dashboard_id,
            "dashboard_config": {
                "title": self.title,
                "charts": self.charts,
                "insights": self.insights or "",
                "summary": self.summary or "",
                "key_metrics": self.key_metrics or []
            },
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "file_url": self.file_url
        }
