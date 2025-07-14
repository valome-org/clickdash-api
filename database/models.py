from datetime import datetime
from typing import Any, Dict, Optional

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
        created_at = getattr(self, 'created_at', None)
        updated_at = getattr(self, 'updated_at', None)
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None
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
        created_at = getattr(self, 'created_at', None)
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
            "created_at": created_at.isoformat() if created_at else None,
            "file_url": self.file_url,
            "user_id": self.user_id
        }


class MetadataElement(Base):
    """Database model for storing metadata elements."""
    __tablename__ = "metadata_elements"

    id = Column(Integer, primary_key=True, index=True)
    element_id = Column(String, unique=True, index=True, nullable=False)
    element_type = Column(String, nullable=False)  # dataset, column, etc.
    element_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Metadata content stored as JSON
    metadata_content = Column(JSON, nullable=False)

    # Classification and organization
    business_domain = Column(String, nullable=True)
    privacy_level = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    categories = Column(JSON, nullable=True)  # Array of categories

    # Quality and validation
    quality_score = Column(String, nullable=True)  # Store as string to handle decimals
    completeness_score = Column(String, nullable=True)
    validation_status = Column(String, default="unknown", nullable=False)
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    parent_element_id = Column(String, nullable=True)
    related_elements = Column(JSON, nullable=True)  # Array of related element IDs

    # User and audit information
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Lineage and versioning
    version = Column(String, default="1.0", nullable=False)
    lineage_info = Column(JSON, nullable=True)

    # Relationships to users
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        quality_score = getattr(self, 'quality_score', None)
        completeness_score = getattr(self, 'completeness_score', None)
        last_validated_at = getattr(self, 'last_validated_at', None)
        created_at = getattr(self, 'created_at', None)
        updated_at = getattr(self, 'updated_at', None)

        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "element_name": self.element_name,
            "display_name": self.display_name,
            "description": self.description,
            "metadata_content": self.metadata_content,
            "business_domain": self.business_domain,
            "privacy_level": self.privacy_level,
            "tags": self.tags or [],
            "categories": self.categories or [],
            "quality_score": float(quality_score) if quality_score else 0.0,
            "completeness_score": float(completeness_score) if completeness_score else 0.0,
            "validation_status": self.validation_status,
            "last_validated_at": last_validated_at.isoformat() if last_validated_at else None,
            "parent_element_id": self.parent_element_id,
            "related_elements": self.related_elements or [],
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "version": self.version,
            "lineage_info": self.lineage_info or {}
        }
