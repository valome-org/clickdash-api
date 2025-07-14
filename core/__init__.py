"""
Core package for AI Dashboard Platform
Contains universal interfaces and base classes for data processing
"""

from .data_sources.base import DataSourceInterface, DataSourceConfig, DataSourceCapabilities
from .data_sources.registry import DataSourceRegistry
from .pipeline.base import DataPipeline, PipelineStage, PipelineConfig
from .pipeline.ingestion import DataIngestionStage, IngestionMode, DataFormat
from .pipeline.normalization import (
    DataNormalizationStage,
    UniversalDataSchema,
    DataType,
    ColumnPurpose
)
from .pipeline.quality_assessment import (
    DataQualityAssessmentStage,
    DataQualityReport,
    QualityIssue,
    QualityIssueType,
    QualityIssueSeverity
)
from .metadata import (
    MetadataExtractor,
    MetadataEnhancementService,
    MetadataValidator,
    DatasetMetadata,
    ColumnMetadata,
    UserEnhancedMetadata,
    MetadataType,
    MetadataStatus,
    MetadataContext
)

__all__ = [
    # Data Sources
    'DataSourceInterface',
    'DataSourceConfig',
    'DataSourceCapabilities',
    'DataSourceRegistry',

    # Pipeline Base
    'DataPipeline',
    'PipelineStage',
    'PipelineConfig',

    # Ingestion
    'DataIngestionStage',
    'IngestionMode',
    'DataFormat',

    # Normalization
    'DataNormalizationStage',
    'UniversalDataSchema',
    'DataType',
    'ColumnPurpose',

    # Quality Assessment
    'DataQualityAssessmentStage',
    'DataQualityReport',
    'QualityIssue',
    'QualityIssueType',
    'QualityIssueSeverity',

    # Metadata Management
    'MetadataExtractor',
    'MetadataEnhancementService',
    'MetadataValidator',
    'DatasetMetadata',
    'ColumnMetadata',
    'UserEnhancedMetadata',
    'MetadataType',
    'MetadataStatus',
    'MetadataContext'
]
