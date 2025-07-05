"""
Base validation classes and interfaces for the validation system.

This module provides the foundational classes and enums used throughout
the validation system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
import pandas as pd


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Represents a single validation issue."""

    id: str = Field(..., description="Unique identifier for this issue")
    severity: ValidationSeverity = Field(..., description="Severity level of the issue")
    message: str = Field(..., description="Human-readable description of the issue")
    field: Optional[str] = Field(None, description="Field name that caused the issue")
    row: Optional[int] = Field(None, description="Row number where issue occurred")
    value: Optional[Any] = Field(None, description="Value that caused the issue")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix for the issue")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            pd.Timestamp: lambda v: v.isoformat() if pd.notna(v) else None,
            datetime: lambda v: v.isoformat(),
        }


class ValidationResult(BaseModel):
    """Results of a validation operation."""

    is_valid: bool = Field(..., description="Whether validation passed")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of validation issues")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the result."""
        self.issues.append(issue)
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]

    def has_errors(self) -> bool:
        """Check if result has any error or critical issues."""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                  for issue in self.issues)

    def get_summary_by_severity(self) -> Dict[str, int]:
        """Get count of issues by severity level."""
        summary = {severity.value: 0 for severity in ValidationSeverity}
        for issue in self.issues:
            summary[issue.severity.value] += 1
        return summary


class ValidatorInterface(ABC):
    """Abstract base class for all validators."""

    @abstractmethod
    async def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        """
        Validate the provided data.

        Args:
            data: DataFrame to validate
            **kwargs: Additional validation parameters

        Returns:
            ValidationResult containing validation outcome and issues
        """
        pass

    @abstractmethod
    def get_validator_info(self) -> Dict[str, Any]:
        """
        Get information about this validator.

        Returns:
            Dictionary containing validator metadata
        """
        pass


class ValidationContext(BaseModel):
    """Context information for validation operations."""

    data_source: Optional[str] = Field(None, description="Source of the data being validated")
    business_domain: Optional[str] = Field(None, description="Business domain/industry context")
    validation_config: Dict[str, Any] = Field(default_factory=dict, description="Validation configuration")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User-specific preferences")
    historical_data: Optional[Dict[str, Any]] = Field(None, description="Historical validation data")
