"""
Core metadata management module for automatic metadata extraction,
user-enhanced metadata, and metadata validation.

This module provides comprehensive metadata management capabilities including:
- Automatic metadata extraction from data sources
- User-enhanced metadata with business context
- Metadata validation and consistency checking
- Metadata lineage tracking
"""

from .extractor import (
    MetadataExtractor,
    ColumnMetadata,
    DatasetMetadata,
    MetadataExtractionResult,
    ColumnPurposeDetector,
    BusinessContextInferencer,
    RelationshipMapper
)

from .enhanced import (
    UserEnhancedMetadata,
    MetadataEnhancementService,
    MetadataEnhancementRequest,
    MetadataEnhancementResult,
    MetadataTemplate,
    BusinessMeaning,
    DataPrivacyLevel,
    SensitivityMarking,
    CustomMetadataField
)

from .validator import (
    MetadataValidator,
    MetadataValidationResult,
    MetadataConsistencyChecker,
    MetadataQualityScorer,
    MetadataRecommendationEngine
)

from .base import (
    MetadataInterface,
    MetadataType,
    MetadataStatus,
    MetadataLineage,
    MetadataContext
)

__all__ = [
    # Automatic Extraction
    "MetadataExtractor",
    "ColumnMetadata",
    "DatasetMetadata",
    "MetadataExtractionResult",
    "ColumnPurposeDetector",
    "BusinessContextInferencer",
    "RelationshipMapper",

    # User Enhancement
    "UserEnhancedMetadata",
    "MetadataEnhancementService",
    "MetadataEnhancementRequest",
    "MetadataEnhancementResult",
    "MetadataTemplate",
    "BusinessMeaning",
    "DataPrivacyLevel",
    "SensitivityMarking",
    "CustomMetadataField",

    # Validation
    "MetadataValidator",
    "MetadataValidationResult",
    "MetadataConsistencyChecker",
    "MetadataQualityScorer",
    "MetadataRecommendationEngine",

    # Base
    "MetadataInterface",
    "MetadataType",
    "MetadataStatus",
    "MetadataLineage",
    "MetadataContext"
]
