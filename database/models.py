from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to dashboards
    dashboards = relationship("Dashboard", back_populates="user")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to user
    user = relationship("User", back_populates="dashboards")

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
            "file_url": self.file_url,
            "user_id": self.user_id
        }
