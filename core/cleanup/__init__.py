"""
Intelligent Data Cleanup Module - Core Components

This module provides comprehensive data cleanup capabilities including:
- AI-powered data cleaning suggestions
- Automated outlier handling
- Smart duplicate resolution
- Missing data imputation strategies
- Data transformation recommendations
"""

from .base import (
    CleanupInterface,
    CleanupResult,
    CleanupIssue,
    CleanupSeverity,
    CleanupContext,
    CleanupStrategy
)
from .outlier_handler import (
    OutlierHandler,
    OutlierDetectionMethod,
    OutlierHandlingStrategy,
    OutlierResult
)
from .duplicate_resolver import (
    DuplicateResolver,
    DuplicateResolutionStrategy,
    DuplicateDetectionType,
    DuplicateResult,
    DuplicateGroup
)
from .imputation_engine import (
    ImputationEngine,
    ImputationStrategy,
    ImputationResult,
    ImputationMethod,
    MissingDataPattern
)
from .transformation_recommender import (
    TransformationRecommender,
    TransformationSuggestion,
    TransformationType,
    TransformationResult,
    TransformationPriority
)

__all__ = [
    # Base interfaces
    "CleanupInterface",
    "CleanupResult",
    "CleanupIssue",
    "CleanupSeverity",
    "CleanupContext",
    "CleanupStrategy",

    # Outlier handling
    "OutlierHandler",
    "OutlierDetectionMethod",
    "OutlierHandlingStrategy",
    "OutlierResult",

    # Duplicate resolution
    "DuplicateResolver",
    "DuplicateResolutionStrategy",
    "DuplicateDetectionType",
    "DuplicateResult",
    "DuplicateGroup",

    # Missing data imputation
    "ImputationEngine",
    "ImputationStrategy",
    "ImputationResult",
    "ImputationMethod",
    "MissingDataPattern",

    # Data transformation
    "TransformationRecommender",
    "TransformationSuggestion",
    "TransformationType",
    "TransformationResult",
    "TransformationPriority"
]
