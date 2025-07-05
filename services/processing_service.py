"""
Data Processing Service - Unified data processing workflows using pipeline stages
"""

import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
from pathlib import Path
import logging

from core.pipeline.base import DataPipeline, PipelineConfig, PipelineStatus
from core.pipeline.ingestion import (
    DataIngestionStage,
    IngestionMode,
    DataFormat,
    ingestion_metrics
)
from core.pipeline.normalization import (
    DataNormalizationStage,
    UniversalDataSchema,
    DataType,
    ColumnPurpose
)
from core.pipeline.quality_assessment import (
    DataQualityAssessmentStage,
    DataQualityReport,
    QualityIssue,
    QualityIssueType
)
from services.data_source_service import data_source_service

logger = logging.getLogger(__name__)


class ProcessingWorkflow:
    """
    Predefined processing workflows for different use cases
    """

    BASIC_PROCESSING = "basic_processing"
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"
    QUALITY_FOCUSED = "quality_focused"
    FAST_INGESTION = "fast_ingestion"
    DATA_EXPLORATION = "data_exploration"


class ProcessingResult:
    """
    Result of data processing with comprehensive metadata
    """

    def __init__(self,
                 data: pd.DataFrame,
                 pipeline_metrics: Dict[str, Any],
                 schema: Optional[UniversalDataSchema] = None,
                 quality_report: Optional[DataQualityReport] = None,
                 processing_id: Optional[str] = None):
        self.data = data
        self.pipeline_metrics = pipeline_metrics
        self.schema = schema
        self.quality_report = quality_report
        self.processing_id = processing_id or str(uuid.uuid4())
        self.processed_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'processing_id': self.processing_id,
            'processed_at': self.processed_at.isoformat(),
            'data_shape': {
                'rows': len(self.data),
                'columns': len(self.data.columns)
            },
            'pipeline_metrics': self.pipeline_metrics,
            'schema': self.schema.dict() if self.schema else None,
            'quality_report': self.quality_report.dict() if self.quality_report else None,
            'data_preview': self.data.head(5).to_dict('records') if not self.data.empty else []
        }


class DataProcessingService:
    """
    Service for comprehensive data processing using pipeline stages
    """

    def __init__(self):
        self.processing_history: List[ProcessingResult] = []
        self.active_pipelines: Dict[str, DataPipeline] = {}

    async def process_file(self,
                          file_path: Union[str, Path],
                          workflow: str = ProcessingWorkflow.COMPREHENSIVE_ANALYSIS,
                          config: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Process a file using specified workflow

        Args:
            file_path: Path to the file to process
            workflow: Processing workflow to use
            config: Additional configuration options

        Returns:
            ProcessingResult: Comprehensive processing result
        """
        try:
            logger.info(f"Starting file processing: {file_path} with workflow: {workflow}")

            # Create pipeline based on workflow
            pipeline = await self._create_pipeline(workflow, config)

            # Execute pipeline - handle file path input
            if isinstance(file_path, (str, Path)):
                # For file inputs, we need to use the ingestion stage directly first
                ingestion_stage = pipeline.get_stage("ingestion")
                if ingestion_stage:
                    # Cast to DataIngestionStage to access proper execute method
                    if isinstance(ingestion_stage, DataIngestionStage):
                        result_data = await ingestion_stage.execute(file_path)
                        # Then run remaining stages
                        for stage in pipeline.stages[1:]:
                            result_data = await stage.run(result_data)
                    else:
                        raise ValueError("First stage must be DataIngestionStage for file inputs")
                else:
                    raise ValueError("No ingestion stage found in pipeline")
            else:
                # This should never happen with current implementation
                raise ValueError("Unsupported input type for file processing")

            # Extract results from pipeline stages
            schema = await self._extract_schema(pipeline)
            quality_report = await self._extract_quality_report(pipeline)

            # Create processing result
            result = ProcessingResult(
                data=result_data,
                pipeline_metrics=pipeline.get_pipeline_metrics(),
                schema=schema,
                quality_report=quality_report
            )

            # Store in history
            self.processing_history.append(result)

            # Record metrics
            await self._record_processing_metrics(result)

            logger.info(f"File processing completed successfully: {result.processing_id}")
            return result

        except Exception as e:
            logger.error(f"File processing failed: {str(e)}")
            raise

    async def process_dataframe(self,
                               data: pd.DataFrame,
                               workflow: str = ProcessingWorkflow.BASIC_PROCESSING,
                               config: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Process a DataFrame using specified workflow

        Args:
            data: DataFrame to process
            workflow: Processing workflow to use
            config: Additional configuration options

        Returns:
            ProcessingResult: Comprehensive processing result
        """
        try:
            logger.info(f"Starting DataFrame processing with workflow: {workflow}")

            # Create pipeline based on workflow
            pipeline = await self._create_pipeline(workflow, config)

            # Execute pipeline
            result_data = await pipeline.execute(data)

            # Extract results from pipeline stages
            schema = await self._extract_schema(pipeline)
            quality_report = await self._extract_quality_report(pipeline)

            # Create processing result
            result = ProcessingResult(
                data=result_data,
                pipeline_metrics=pipeline.get_pipeline_metrics(),
                schema=schema,
                quality_report=quality_report
            )

            # Store in history
            self.processing_history.append(result)

            logger.info(f"DataFrame processing completed successfully: {result.processing_id}")
            return result

        except Exception as e:
            logger.error(f"DataFrame processing failed: {str(e)}")
            raise

    async def _create_pipeline(self, workflow: str, config: Optional[Dict[str, Any]] = None) -> DataPipeline:
        """
        Create pipeline based on workflow type
        """
        config = config or {}

        if workflow == ProcessingWorkflow.BASIC_PROCESSING:
            return await self._create_basic_pipeline(config)
        elif workflow == ProcessingWorkflow.COMPREHENSIVE_ANALYSIS:
            return await self._create_comprehensive_pipeline(config)
        elif workflow == ProcessingWorkflow.QUALITY_FOCUSED:
            return await self._create_quality_focused_pipeline(config)
        elif workflow == ProcessingWorkflow.FAST_INGESTION:
            return await self._create_fast_ingestion_pipeline(config)
        elif workflow == ProcessingWorkflow.DATA_EXPLORATION:
            return await self._create_data_exploration_pipeline(config)
        else:
            raise ValueError(f"Unknown workflow: {workflow}")

    async def _create_basic_pipeline(self, config: Dict[str, Any]) -> DataPipeline:
        """
        Create basic processing pipeline (ingestion + basic normalization)
        """
        pipeline_config = PipelineConfig(
            name="basic_processing",
            description="Basic data processing with ingestion and normalization"
        )

        pipeline = BasicDataPipeline(pipeline_config)

        # Add ingestion stage
        ingestion_stage = DataIngestionStage(
            name="ingestion",
            config={
                "mode": config.get("ingestion_mode", "batch"),
                "chunk_size": config.get("chunk_size", 10000),
                "format_detection": config.get("format_detection", True)
            }
        )
        pipeline.add_stage(ingestion_stage)

        # Add normalization stage
        normalization_stage = DataNormalizationStage(
            name="normalization",
            config={
                "normalize_column_names": config.get("normalize_column_names", True),
                "infer_data_types": config.get("infer_data_types", True),
                "detect_relationships": config.get("detect_relationships", False)
            }
        )
        pipeline.add_stage(normalization_stage)

        return pipeline

    async def _create_comprehensive_pipeline(self, config: Dict[str, Any]) -> DataPipeline:
        """
        Create comprehensive processing pipeline (all stages)
        """
        pipeline_config = PipelineConfig(
            name="comprehensive_analysis",
            description="Comprehensive data processing with all stages"
        )

        pipeline = ComprehensiveDataPipeline(pipeline_config)

        # Add ingestion stage
        ingestion_stage = DataIngestionStage(
            name="ingestion",
            config={
                "mode": config.get("ingestion_mode", "batch"),
                "chunk_size": config.get("chunk_size", 10000),
                "format_detection": True
            }
        )
        pipeline.add_stage(ingestion_stage)

        # Add normalization stage
        normalization_stage = DataNormalizationStage(
            name="normalization",
            config={
                "normalize_column_names": True,
                "infer_data_types": True,
                "detect_relationships": True
            }
        )
        pipeline.add_stage(normalization_stage)

        # Add quality assessment stage
        quality_stage = DataQualityAssessmentStage(
            name="quality_assessment",
            config={
                "missing_threshold": config.get("missing_threshold", 0.1),
                "outlier_method": config.get("outlier_method", "iqr"),
                "outlier_threshold": config.get("outlier_threshold", 3.0)
            }
        )
        pipeline.add_stage(quality_stage)

        return pipeline

    async def _create_quality_focused_pipeline(self, config: Dict[str, Any]) -> DataPipeline:
        """
        Create quality-focused pipeline (minimal processing, extensive quality checks)
        """
        pipeline_config = PipelineConfig(
            name="quality_focused",
            description="Quality-focused processing with extensive data quality assessment"
        )

        pipeline = QualityFocusedDataPipeline(pipeline_config)

        # Add basic ingestion
        ingestion_stage = DataIngestionStage(
            name="ingestion",
            config={
                "mode": "batch",
                "format_detection": True
            }
        )
        pipeline.add_stage(ingestion_stage)

        # Add comprehensive quality assessment
        quality_stage = DataQualityAssessmentStage(
            name="quality_assessment",
            config={
                "missing_threshold": 0.05,  # More strict
                "outlier_method": "iqr",
                "outlier_threshold": 2.0  # More sensitive
            }
        )
        pipeline.add_stage(quality_stage)

        return pipeline

    async def _create_fast_ingestion_pipeline(self, config: Dict[str, Any]) -> DataPipeline:
        """
        Create fast ingestion pipeline (minimal processing for speed)
        """
        pipeline_config = PipelineConfig(
            name="fast_ingestion",
            description="Fast data ingestion with minimal processing"
        )

        pipeline = FastIngestionDataPipeline(pipeline_config)

        # Add optimized ingestion stage
        ingestion_stage = DataIngestionStage(
            name="fast_ingestion",
            config={
                "mode": "streaming",
                "chunk_size": config.get("chunk_size", 50000),
                "max_memory_mb": config.get("max_memory_mb", 1024),
                "format_detection": config.get("format_detection", False)
            }
        )
        pipeline.add_stage(ingestion_stage)

        return pipeline

    async def _create_data_exploration_pipeline(self, config: Dict[str, Any]) -> DataPipeline:
        """
        Create data exploration pipeline (focused on understanding data structure)
        """
        pipeline_config = PipelineConfig(
            name="data_exploration",
            description="Data exploration focused on understanding structure and patterns"
        )

        pipeline = DataExplorationDataPipeline(pipeline_config)

        # Add ingestion
        ingestion_stage = DataIngestionStage(
            name="ingestion",
            config={
                "mode": "batch",
                "format_detection": True
            }
        )
        pipeline.add_stage(ingestion_stage)

        # Add normalization with relationship detection
        normalization_stage = DataNormalizationStage(
            name="normalization",
            config={
                "normalize_column_names": True,
                "infer_data_types": True,
                "detect_relationships": True
            }
        )
        pipeline.add_stage(normalization_stage)

        return pipeline

    async def _extract_schema(self, pipeline: DataPipeline) -> Optional[UniversalDataSchema]:
        """
        Extract schema from normalization stage
        """
        try:
            normalization_stage = pipeline.get_stage("normalization")
            if normalization_stage:
                from core.pipeline.normalization import DataNormalizationStage
                if isinstance(normalization_stage, DataNormalizationStage) and hasattr(normalization_stage, 'schema'):
                    return normalization_stage.schema
        except Exception as e:
            logger.error(f"Schema extraction failed: {str(e)}")
        return None

    async def _extract_quality_report(self, pipeline: DataPipeline) -> Optional[DataQualityReport]:
        """
        Extract quality report from quality assessment stage
        """
        try:
            quality_stage = pipeline.get_stage("quality_assessment")
            if quality_stage:
                from core.pipeline.quality_assessment import DataQualityAssessmentStage
                if isinstance(quality_stage, DataQualityAssessmentStage) and hasattr(quality_stage, 'get_quality_report'):
                    return quality_stage.get_quality_report()
        except Exception as e:
            logger.error(f"Quality report extraction failed: {str(e)}")
        return None

    async def _record_processing_metrics(self, result: ProcessingResult):
        """
        Record processing metrics
        """
        try:
            # Record ingestion metrics if available
            if result.pipeline_metrics:
                ingestion_metrics.record_ingestion(
                    ingestion_id=result.processing_id,
                    success=True,
                    rows_ingested=len(result.data),
                    memory_used_mb=result.data.memory_usage(deep=True).sum() / 1024 / 1024,
                    execution_time_seconds=result.pipeline_metrics.get('metrics', {}).get('total_execution_time', 0),
                    source_type='processed_data'
                )
        except Exception as e:
            logger.error(f"Metrics recording failed: {str(e)}")

    def get_processing_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get processing history
        """
        history = [result.to_dict() for result in self.processing_history]
        if limit:
            return history[-limit:]
        return history

    def get_processing_result(self, processing_id: str) -> Optional[ProcessingResult]:
        """
        Get specific processing result by ID
        """
        for result in self.processing_history:
            if result.processing_id == processing_id:
                return result
        return None

    async def get_processing_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing metrics
        """
        return {
            'total_processed': len(self.processing_history),
            'active_pipelines': len(self.active_pipelines),
            'ingestion_metrics': ingestion_metrics.get_metrics(),
            'recent_results': [
                {
                    'processing_id': result.processing_id,
                    'processed_at': result.processed_at.isoformat(),
                    'quality_score': result.quality_report.overall_quality_score if result.quality_report else None,
                    'rows': len(result.data),
                    'columns': len(result.data.columns)
                }
                for result in self.processing_history[-10:]
            ]
        }


# Specific pipeline implementations

class BasicDataPipeline(DataPipeline):
    """Basic data processing pipeline"""
    pass


class ComprehensiveDataPipeline(DataPipeline):
    """Comprehensive data processing pipeline"""
    pass


class QualityFocusedDataPipeline(DataPipeline):
    """Quality-focused data processing pipeline"""
    pass


class FastIngestionDataPipeline(DataPipeline):
    """Fast ingestion data processing pipeline"""
    pass


class DataExplorationDataPipeline(DataPipeline):
    """Data exploration pipeline"""
    pass


# Global service instance
data_processing_service = DataProcessingService()


# Workflow templates for easy access
WORKFLOW_TEMPLATES = {
    ProcessingWorkflow.BASIC_PROCESSING: {
        "name": "Basic Processing",
        "description": "Basic data ingestion and normalization",
        "stages": ["ingestion", "normalization"],
        "recommended_for": ["Simple data cleanup", "Quick data preparation"],
        "estimated_time": "Fast"
    },
    ProcessingWorkflow.COMPREHENSIVE_ANALYSIS: {
        "name": "Comprehensive Analysis",
        "description": "Full data processing with quality assessment",
        "stages": ["ingestion", "normalization", "quality_assessment"],
        "recommended_for": ["Data analysis", "Dashboard preparation", "Data quality audits"],
        "estimated_time": "Medium"
    },
    ProcessingWorkflow.QUALITY_FOCUSED: {
        "name": "Quality Focused",
        "description": "Extensive data quality checks with minimal processing",
        "stages": ["ingestion", "quality_assessment"],
        "recommended_for": ["Data validation", "Quality audits", "Compliance checks"],
        "estimated_time": "Fast"
    },
    ProcessingWorkflow.FAST_INGESTION: {
        "name": "Fast Ingestion",
        "description": "Optimized for speed with large datasets",
        "stages": ["fast_ingestion"],
        "recommended_for": ["Large files", "Time-critical processing", "Data migration"],
        "estimated_time": "Very Fast"
    },
    ProcessingWorkflow.DATA_EXPLORATION: {
        "name": "Data Exploration",
        "description": "Focused on understanding data structure and relationships",
        "stages": ["ingestion", "normalization"],
        "recommended_for": ["Data discovery", "Schema analysis", "Relationship mapping"],
        "estimated_time": "Medium"
    }
}
