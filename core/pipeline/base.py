"""
Base Data Pipeline Classes
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Status of pipeline execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStageType(Enum):
    """Types of pipeline stages"""
    INGESTION = "ingestion"
    VALIDATION = "validation"
    CLEANING = "cleaning"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    AGGREGATION = "aggregation"
    OUTPUT = "output"


class PipelineConfig(BaseModel):
    """Configuration for data pipeline"""
    name: str
    description: Optional[str] = None
    stages: List[Dict[str, Any]] = Field(default_factory=list)
    max_parallel_stages: int = 3
    timeout_seconds: int = 300
    retry_count: int = 2
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class PipelineStage(ABC):
    """
    Base class for all pipeline stages
    """

    def __init__(self,
                 name: str,
                 stage_type: PipelineStageType,
                 config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.stage_type = stage_type
        self.config = config or {}
        self.status = PipelineStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.metrics: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the pipeline stage

        Args:
            data: Input DataFrame

        Returns:
            pd.DataFrame: Processed DataFrame
        """
        pass

    @abstractmethod
    async def validate_inputs(self, data: pd.DataFrame) -> bool:
        """
        Validate inputs before processing

        Args:
            data: Input DataFrame

        Returns:
            bool: True if inputs are valid
        """
        pass

    async def run(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Run the pipeline stage with error handling and metrics
        """
        try:
            self.status = PipelineStatus.RUNNING
            self.start_time = datetime.now()

            # Validate inputs
            if not await self.validate_inputs(data):
                raise ValueError(f"Input validation failed for stage: {self.name}")

            # Execute stage
            result = await self.execute(data)

            # Record metrics
            self.metrics.update({
                'input_rows': len(data),
                'output_rows': len(result),
                'execution_time': (datetime.now() - self.start_time).total_seconds()
            })

            self.status = PipelineStatus.COMPLETED
            self.end_time = datetime.now()

            logger.info(f"Pipeline stage '{self.name}' completed successfully")
            return result

        except Exception as e:
            self.status = PipelineStatus.FAILED
            self.error_message = str(e)
            self.end_time = datetime.now()
            logger.error(f"Pipeline stage '{self.name}' failed: {str(e)}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        return {
            'stage_name': self.name,
            'stage_type': self.stage_type.value,
            'status': self.status.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'metrics': self.metrics
        }


class DataPipeline(ABC):
    """
    Base class for data processing pipelines
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stages: List[PipelineStage] = []
        self.status = PipelineStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.pipeline_metrics: Dict[str, Any] = {}

    def add_stage(self, stage: PipelineStage):
        """Add a stage to the pipeline"""
        self.stages.append(stage)

    def remove_stage(self, stage_name: str) -> bool:
        """Remove a stage from the pipeline"""
        for i, stage in enumerate(self.stages):
            if stage.name == stage_name:
                del self.stages[i]
                return True
        return False

    def get_stage(self, stage_name: str) -> Optional[PipelineStage]:
        """Get a stage by name"""
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        return None

    async def execute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the entire pipeline

        Args:
            data: Input DataFrame

        Returns:
            pd.DataFrame: Final processed DataFrame
        """
        try:
            self.status = PipelineStatus.RUNNING
            self.start_time = datetime.now()

            logger.info(f"Starting pipeline execution: {self.config.name}")

            current_data = data
            stage_results = []

            for stage in self.stages:
                logger.info(f"Executing stage: {stage.name}")
                current_data = await stage.run(current_data)
                stage_results.append(stage.get_metrics())

            # Calculate pipeline metrics
            self.pipeline_metrics = {
                'total_stages': len(self.stages),
                'successful_stages': len([s for s in self.stages if s.status == PipelineStatus.COMPLETED]),
                'failed_stages': len([s for s in self.stages if s.status == PipelineStatus.FAILED]),
                'input_rows': len(data),
                'output_rows': len(current_data),
                'total_execution_time': (datetime.now() - self.start_time).total_seconds(),
                'stages': stage_results
            }

            self.status = PipelineStatus.COMPLETED
            self.end_time = datetime.now()

            logger.info(f"Pipeline '{self.config.name}' completed successfully")
            return current_data

        except Exception as e:
            self.status = PipelineStatus.FAILED
            self.error_message = str(e)
            self.end_time = datetime.now()
            logger.error(f"Pipeline '{self.config.name}' failed: {str(e)}")
            raise

    async def validate_pipeline(self) -> Dict[str, Any]:
        """
        Validate the entire pipeline configuration

        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stage_validations': []
        }

        # Check if pipeline has stages
        if not self.stages:
            validation_results['errors'].append("Pipeline has no stages")
            validation_results['valid'] = False

        # Check stage dependencies and types
        stage_types = [stage.stage_type for stage in self.stages]

        # Warn if no ingestion stage
        if PipelineStageType.INGESTION not in stage_types:
            validation_results['warnings'].append("No ingestion stage found")

        # Warn if no validation stage
        if PipelineStageType.VALIDATION not in stage_types:
            validation_results['warnings'].append("No validation stage found")

        # Check for duplicate stage names
        stage_names = [stage.name for stage in self.stages]
        if len(stage_names) != len(set(stage_names)):
            validation_results['errors'].append("Duplicate stage names found")
            validation_results['valid'] = False

        return validation_results

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics"""
        return {
            'pipeline_name': self.config.name,
            'status': self.status.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'metrics': self.pipeline_metrics
        }

    def reset(self):
        """Reset pipeline state"""
        self.status = PipelineStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.pipeline_metrics = {}

        # Reset all stages
        for stage in self.stages:
            stage.status = PipelineStatus.PENDING
            stage.start_time = None
            stage.end_time = None
            stage.error_message = None
            stage.metrics = {}
