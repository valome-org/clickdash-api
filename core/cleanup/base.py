"""
Base interfaces and classes for data cleanup operations.

This module provides the foundational interfaces and models for all data cleanup operations,
including outlier handling, duplicate resolution, missing data imputation, and transformations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Set
from datetime import datetime
from enum import Enum
import pandas as pd
from pydantic import BaseModel, Field
import uuid


class CleanupSeverity(str, Enum):
    """Severity levels for cleanup issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CleanupStrategy(str, Enum):
    """Available cleanup strategies."""
    AUTOMATIC = "automatic"  # Apply cleanup automatically
    SUGGEST = "suggest"      # Only suggest cleanup actions
    INTERACTIVE = "interactive"  # Require user confirmation
    CONSERVATIVE = "conservative"  # Only safe, reversible operations


class CleanupIssue(BaseModel):
    """Represents a data quality issue that can be cleaned."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique issue identifier")
    issue_type: str = Field(..., description="Type of data quality issue")
    severity: CleanupSeverity = Field(..., description="Severity of the issue")
    message: str = Field(..., description="Human-readable description of the issue")
    field: str = Field(..., description="Column/field name where issue was found")
    row_indices: List[int] = Field(default_factory=list, description="Row indices affected by this issue")
    affected_values: List[Any] = Field(default_factory=list, description="Values affected by this issue")

    # Cleanup recommendations
    suggested_action: str = Field(..., description="Suggested cleanup action")
    confidence: float = Field(default=0.0, description="Confidence in the suggested action (0-1)")
    estimated_impact: str = Field(..., description="Estimated impact of applying the cleanup")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional issue metadata")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When issue was detected")


class CleanupResult(BaseModel):
    """Results of a cleanup operation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique result identifier")
    is_successful: bool = Field(..., description="Whether cleanup was successful")

    # Data results
    cleaned_data: Optional[Any] = Field(None, description="Cleaned dataset")
    issues_found: List[CleanupIssue] = Field(default_factory=list, description="Issues identified")
    issues_resolved: List[str] = Field(default_factory=list, description="Issue IDs that were resolved")

    # Statistics
    rows_affected: int = Field(default=0, description="Number of rows affected by cleanup")
    columns_affected: int = Field(default=0, description="Number of columns affected by cleanup")
    data_quality_improvement: float = Field(default=0.0, description="Improvement in data quality score")

    # Execution info
    execution_time_ms: float = Field(default=0.0, description="Time taken for cleanup operation")
    cleanup_strategy_used: CleanupStrategy = Field(..., description="Strategy used for cleanup")

    # Change tracking
    applied_transformations: List[Dict[str, Any]] = Field(default_factory=list, description="List of transformations applied")
    reversible: bool = Field(default=True, description="Whether cleanup operations are reversible")
    rollback_info: Optional[Dict[str, Any]] = Field(None, description="Information needed to rollback changes")

    # Recommendations
    additional_recommendations: List[str] = Field(default_factory=list, description="Additional cleanup recommendations")

    def add_issue(self, issue: CleanupIssue) -> None:
        """Add a cleanup issue to the result."""
        self.issues_found.append(issue)

    def mark_issue_resolved(self, issue_id: str) -> None:
        """Mark an issue as resolved."""
        if issue_id not in self.issues_resolved:
            self.issues_resolved.append(issue_id)


class CleanupContext(BaseModel):
    """Context information for cleanup operations."""

    dataset_name: Optional[str] = Field(None, description="Name of the dataset being cleaned")
    data_source: Optional[str] = Field(None, description="Source of the data")
    business_domain: Optional[str] = Field(None, description="Business domain context")

    # User preferences
    cleanup_strategy: CleanupStrategy = Field(default=CleanupStrategy.SUGGEST, description="Preferred cleanup strategy")
    aggressiveness_level: float = Field(default=0.5, description="Cleanup aggressiveness (0-1, conservative to aggressive)")
    preserve_original: bool = Field(default=True, description="Whether to preserve original data")

    # Constraints
    allowed_transformations: Optional[Set[str]] = Field(None, description="Allowed transformation types")
    forbidden_operations: Optional[Set[str]] = Field(None, description="Operations that should not be performed")
    column_importance: Dict[str, float] = Field(default_factory=dict, description="Importance weight for each column")

    # Performance constraints
    max_execution_time_ms: Optional[float] = Field(None, description="Maximum allowed execution time")
    memory_limit_mb: Optional[float] = Field(None, description="Memory usage limit")


class CleanupInterface(ABC):
    """Abstract interface for all data cleanup operations."""

    @abstractmethod
    async def clean(self, data: pd.DataFrame, context: Optional[CleanupContext] = None, **kwargs) -> CleanupResult:
        """
        Perform cleanup operation on the provided data.

        Args:
            data: DataFrame to clean
            context: Cleanup context with preferences and constraints
            **kwargs: Additional cleanup parameters

        Returns:
            CleanupResult with cleaned data and operation details
        """
        pass

    @abstractmethod
    def get_cleanup_info(self) -> Dict[str, Any]:
        """
        Get information about this cleanup operation.

        Returns:
            Dictionary with cleanup operation details
        """
        pass

    @abstractmethod
    async def analyze_data(self, data: pd.DataFrame, context: Optional[CleanupContext] = None) -> List[CleanupIssue]:
        """
        Analyze data to identify cleanup opportunities without performing cleanup.

        Args:
            data: DataFrame to analyze
            context: Analysis context

        Returns:
            List of identified cleanup issues
        """
        pass

    def validate_input(self, data: pd.DataFrame) -> bool:
        """
        Validate input data before cleanup.

        Args:
            data: DataFrame to validate

        Returns:
            True if input is valid for cleanup
        """
        if data is None:
            return False
        if hasattr(data, 'empty'):
            return len(data) > 0
        return True

    def estimate_impact(self, data: pd.DataFrame, issues: List[CleanupIssue]) -> Dict[str, Any]:
        """
        Estimate the impact of resolving identified issues.

        Args:
            data: Original DataFrame
            issues: List of issues to resolve

        Returns:
            Dictionary with impact estimates
        """
        total_rows = len(data)
        affected_rows = set()

        for issue in issues:
            affected_rows.update(issue.row_indices)

        return {
            "total_rows": total_rows,
            "affected_rows": len(affected_rows),
            "affected_percentage": (len(affected_rows) / total_rows) * 100 if total_rows > 0 else 0,
            "issues_count": len(issues),
            "high_severity_issues": len([i for i in issues if i.severity in [CleanupSeverity.CRITICAL, CleanupSeverity.HIGH]])
        }
