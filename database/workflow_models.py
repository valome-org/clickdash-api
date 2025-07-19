"""
Additional Database Models for 8-Phase Workflow System.

These models track the complete workflow state and enable proper
data processing, validation, and approval workflows.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum as PyEnum

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text, Float, Enum)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.models import Base

# Import existing User model for relationships
# Note: We'll add relationships to User model separately

# Enums
class WorkflowStatus(PyEnum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DataSourceType(PyEnum):
    EXCEL = "excel"
    CSV = "csv"
    DATABASE = "database"
    API = "api"
    GOOGLE_SHEETS = "google_sheets"
    JSON = "json"

class ProcessingStatus(PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ApprovalStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"


# Core Workflow Model
class Workflow(Base):
    """Main workflow tracking model for 8-phase system."""
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Status and phase tracking
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.CREATED)
    current_phase = Column(String(50))  # "phase_1", "phase_2", etc.
    phases_completed = Column(JSON)  # Array of completed phases

    # Configuration and data
    configuration = Column(JSON)  # Workflow configuration
    ai_analysis_results = Column(JSON)  # AI analysis from each phase

    # User and timestamps
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships (will reference User from existing models)
    # user = relationship("User", back_populates="workflows")  # Added to User model
    data_sources = relationship("DataSource", back_populates="workflow")
    processing_jobs = relationship("DataProcessingJob", back_populates="workflow")
    validations = relationship("DataValidation", back_populates="workflow")
    cleanups = relationship("DataCleanup", back_populates="workflow")
    approvals = relationship("Approval", back_populates="workflow")
    dashboard_versions = relationship("DashboardVersion", back_populates="workflow")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        created_at = getattr(self, 'created_at', None)
        updated_at = getattr(self, 'updated_at', None)
        completed_at = getattr(self, 'completed_at', None)
        status = getattr(self, 'status', None)
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "status": status.value if status else None,
            "current_phase": self.current_phase,
            "phases_completed": self.phases_completed or [],
            "configuration": self.configuration or {},
            "ai_analysis_results": self.ai_analysis_results or {},
            "user_id": self.user_id,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
        }


# Phase 1: Data Sources
class DataSource(Base):
    """Track connected data sources."""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)

    # Source details
    name = Column(String(255), nullable=False)
    source_type = Column(Enum(DataSourceType), nullable=False)
    connection_params = Column(JSON)  # Connection configuration
    file_path = Column(String(500))  # For file-based sources

    # Metadata and schema
    schema_info = Column(JSON)  # Detected schema information
    row_count = Column(Integer)
    column_count = Column(Integer)
    data_preview = Column(JSON)  # Sample rows

    # Status and validation
    status = Column(String(50), default="connected")
    last_tested_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workflow = relationship("Workflow", back_populates="data_sources")


# Phase 2: Data Processing
class DataProcessingJob(Base):
    """Track data processing operations."""
    __tablename__ = "data_processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)

    # Processing details
    processing_type = Column(String(100))  # "ingestion", "normalization", "profiling"
    parameters = Column(JSON)  # Processing parameters

    # Results and metrics
    input_rows = Column(Integer)
    output_rows = Column(Integer)
    processing_duration_ms = Column(Float)
    quality_metrics = Column(JSON)

    # Status tracking
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    progress_percentage = Column(Float, default=0.0)
    error_message = Column(Text)

    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow", back_populates="processing_jobs")
    data_source = relationship("DataSource")


# Phase 3: Data Validation
class DataValidation(Base):
    """Track data validation results."""
    __tablename__ = "data_validations"

    id = Column(Integer, primary_key=True, index=True)
    validation_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    processing_job_id = Column(Integer, ForeignKey("data_processing_jobs.id"))

    # Validation configuration
    validation_rules = Column(JSON)  # Applied validation rules
    validation_scope = Column(String(100))  # "full", "sample", "columns"

    # Results
    overall_quality_score = Column(Float)
    total_rows_validated = Column(Integer)
    valid_rows = Column(Integer)
    invalid_rows = Column(Integer)

    # Issues and recommendations
    validation_issues = Column(JSON)  # Detailed issues found
    recommendations = Column(JSON)  # AI recommendations
    critical_issues_count = Column(Integer, default=0)
    warning_issues_count = Column(Integer, default=0)

    # Status and timestamps
    status = Column(String(50), default="completed")
    validated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow", back_populates="validations")
    processing_job = relationship("DataProcessingJob")


# Phase 4: Data Cleanup
class DataCleanup(Base):
    """Track data cleanup operations."""
    __tablename__ = "data_cleanups"

    id = Column(Integer, primary_key=True, index=True)
    cleanup_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    validation_id = Column(Integer, ForeignKey("data_validations.id"))

    # Cleanup configuration
    cleanup_rules = Column(JSON)  # Applied cleanup rules
    cleanup_strategy = Column(String(100))  # "automatic", "guided", "manual"

    # Results
    original_rows = Column(Integer)
    cleaned_rows = Column(Integer)
    removed_rows = Column(Integer)
    modified_rows = Column(Integer)

    # Cleanup operations performed
    operations_performed = Column(JSON)  # List of cleanup operations
    cleanup_summary = Column(JSON)  # Summary of changes

    # Status and timestamps
    status = Column(String(50), default="completed")
    cleaned_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow", back_populates="cleanups")
    validation = relationship("DataValidation")


# Phase 6+7: Approval System
class Approval(Base):
    """Track approval requests and decisions."""
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    approval_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)

    # Approval details
    approval_type = Column(String(100))  # "dashboard_config", "data_cleanup", "export"
    phase = Column(String(50))  # Which phase requires approval

    # Request details
    item_description = Column(Text)
    request_data = Column(JSON)  # Data requiring approval
    ai_recommendations = Column(JSON)  # AI analysis and suggestions

    # Decision
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approver_id = Column(Integer, ForeignKey("users.id"))
    decision_notes = Column(Text)
    decision_data = Column(JSON)  # Approved/modified configuration

    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    workflow = relationship("Workflow", back_populates="approvals")
    # approver = relationship("User")  # Points to existing User model


# Phase 8: Dashboard Versions
class DashboardVersion(Base):
    """Track dashboard versions and changes."""
    __tablename__ = "dashboard_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=False)

    # Version details
    version_number = Column(String(50), nullable=False)  # "1.0", "1.1", etc.
    version_name = Column(String(255))  # Optional name
    description = Column(Text)

    # Configuration
    dashboard_config = Column(JSON)  # Full dashboard configuration
    generation_params = Column(JSON)  # Parameters used for generation
    ai_analysis = Column(JSON)  # AI analysis results

    # Status
    status = Column(String(50), default="draft")  # draft, published, archived
    is_current = Column(Boolean, default=False)

    # Timestamps
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True))

    workflow = relationship("Workflow", back_populates="dashboard_versions")
    # dashboard = relationship("Dashboard")  # Points to existing Dashboard model
    # creator = relationship("User")


# Export System
class ExportJob(Base):
    """Track dashboard export operations."""
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True, index=True)
    export_id = Column(String, unique=True, index=True, nullable=False)
    dashboard_version_id = Column(Integer, ForeignKey("dashboard_versions.id"))

    # Export details
    export_format = Column(String(100))  # "pdf", "png", "html", "embed"
    export_params = Column(JSON)  # Export-specific parameters
    output_path = Column(String(500))

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    progress_percentage = Column(Float, default=0.0)
    error_message = Column(Text)

    # User and timestamps
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    dashboard_version = relationship("DashboardVersion")
    # user = relationship("User")


# Notification System
class Notification(Base):
    """Track system notifications."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)

    # Notification details
    notification_type = Column(String(100))  # "approval_required", "workflow_completed"
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Delivery channels
    channels = Column(JSON)  # ["email", "sms", "in_app"]

    # Status
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))

    # user = relationship("User")  # Points to existing User model
    workflow = relationship("Workflow")


# Update User model to include new relationships
# Add this to your existing User model in database/models.py:
"""
# Add these relationships to your existing User class:
workflows = relationship("Workflow", back_populates="user")
approvals_made = relationship("Approval", foreign_keys="Approval.approver_id")
dashboard_versions_created = relationship("DashboardVersion", foreign_keys="DashboardVersion.created_by")
export_jobs = relationship("ExportJob", back_populates="user")
notifications = relationship("Notification", back_populates="user")
"""
