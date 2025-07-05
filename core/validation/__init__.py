"""
Core validation module for data validation, schema validation, and business rules

This module provides comprehensive data validation capabilities including:
- Schema validation and evolution tracking
- Business rule validation engine
- Data profiling and analysis
- Custom validation rule creation
"""

from .schema_validator import (
    SchemaValidator,
    SchemaValidationResult,
    SchemaEvolutionTracker,
    SchemaCompatibilityChecker,
    Schema,
    ColumnSchema,
    DataType,
    ColumnConstraint
)

from .business_rules import (
    BusinessRuleEngine,
    BusinessRule,
    RuleValidationResult,
    RuleConflictDetector,
    IndustryTemplates,
    RuleCondition,
    RuleOperator,
    LogicalOperator
)

from .profiler import (
    DataProfiler,
    ProfileResult,
    StatisticalAnalyzer,
    PatternRecognizer,
    ProfilingRecommendations
)

from .base import (
    ValidationResult,
    ValidationSeverity,
    ValidationIssue,
    ValidatorInterface,
    ValidationContext
)

__all__ = [
    # Schema validation
    "SchemaValidator",
    "SchemaValidationResult",
    "SchemaEvolutionTracker",
    "SchemaCompatibilityChecker",
    "Schema",
    "ColumnSchema",
    "DataType",
    "ColumnConstraint",

    # Business rules
    "BusinessRuleEngine",
    "BusinessRule",
    "RuleValidationResult",
    "RuleConflictDetector",
    "IndustryTemplates",
    "RuleCondition",
    "RuleOperator",
    "LogicalOperator",

    # Data profiling
    "DataProfiler",
    "ProfileResult",
    "StatisticalAnalyzer",
    "PatternRecognizer",
    "ProfilingRecommendations",

    # Base validation
    "ValidationResult",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidatorInterface",
    "ValidationContext"
]
