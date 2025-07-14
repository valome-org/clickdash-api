"""
Base interfaces and types for metadata management system.

This module defines the fundamental interfaces and data types used
throughout the metadata management system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class MetadataType(str, Enum):
    """Types of metadata that can be managed."""
    COLUMN = "column"
    DATASET = "dataset"
    RELATIONSHIP = "relationship"
    BUSINESS_CONTEXT = "business_context"
    DATA_LINEAGE = "data_lineage"
    QUALITY_METRICS = "quality_metrics"
    PRIVACY_CLASSIFICATION = "privacy_classification"


class MetadataStatus(str, Enum):
    """Status of metadata information."""
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class DataPrivacyLevel(str, Enum):
    """Data privacy and sensitivity levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class MetadataLineage(BaseModel):
    """Tracks the lineage and history of metadata."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = Field(..., description="Source identifier")
    operation: str = Field(..., description="Operation that created this metadata")
    created_by: Optional[str] = Field(None, description="Who created this metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_lineage_id: Optional[str] = Field(None, description="Parent lineage reference")
    confidence_score: float = Field(default=0.0, description="Confidence in this metadata")
    validation_status: MetadataStatus = Field(default=MetadataStatus.UNKNOWN)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional lineage metadata")


class MetadataContext(BaseModel):
    """Context information for metadata operations."""

    dataset_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    environment: str = "development"
    domain: Optional[str] = None
    industry: Optional[str] = None
    use_case: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class MetadataInterface(ABC):
    """
    Base interface for all metadata management components.
    """

    def __init__(self, context: Optional[MetadataContext] = None):
        self.context = context or MetadataContext()
        self.lineage: List[MetadataLineage] = []

    @abstractmethod
    async def extract_metadata(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Extract metadata from data source."""
        pass

    @abstractmethod
    async def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata for consistency and quality."""
        pass

    def add_lineage(self, lineage: MetadataLineage):
        """Add lineage information."""
        self.lineage.append(lineage)

    def get_lineage_history(self) -> List[MetadataLineage]:
        """Get complete lineage history."""
        return self.lineage.copy()
