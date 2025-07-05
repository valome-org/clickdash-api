"""
Data Ingestion Pipeline - Universal data intake from any source
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from datetime import datetime
import pandas as pd
from pathlib import Path
from enum import Enum
import logging

from .base import PipelineStage, PipelineStageType, PipelineStatus
from core.data_sources.base import DataSourceInterface
from core.data_sources.registry import data_source_registry

logger = logging.getLogger(__name__)


class IngestionMode(Enum):
    """Different modes of data ingestion"""
    BATCH = "batch"
    STREAMING = "streaming"
    INCREMENTAL = "incremental"
    REAL_TIME = "real_time"


class DataFormat(Enum):
    """Supported data formats for ingestion"""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    API = "api"
    DATABASE = "database"
    UNKNOWN = "unknown"


class DataIngestionStage(PipelineStage):
    """
    Data ingestion stage that handles data intake from various sources
    """

    def __init__(self,
                 name: str = "data_ingestion",
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name, PipelineStageType.INGESTION, config)
        config = config or {}
        self.ingestion_mode = IngestionMode(config.get("mode", "batch"))
        self.chunk_size = config.get("chunk_size", 10000)
        self.max_memory_mb = config.get("max_memory_mb", 512)
        self.format_detection = config.get("format_detection", True)
        self.data_source: Optional[DataSourceInterface] = None

    async def validate_inputs(self, data: Union[pd.DataFrame, str, Path]) -> bool:
        """
        Validate inputs before ingestion
        """
        try:
            if isinstance(data, pd.DataFrame):
                return not data.empty
            elif isinstance(data, (str, Path)):
                return Path(data).exists()
            else:
                logger.error(f"Unsupported input type: {type(data)}")
                return False
        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return False

    async def execute(self, data: Union[pd.DataFrame, str, Path]) -> pd.DataFrame:
        """
        Execute data ingestion
        """
        try:
            if isinstance(data, pd.DataFrame):
                # Data is already in DataFrame format
                return await self._process_dataframe(data)
            elif isinstance(data, (str, Path)):
                # Data is from a file source
                return await self._ingest_from_file(Path(data))
            else:
                raise ValueError(f"Unsupported data input type: {type(data)}")

        except Exception as e:
            logger.error(f"Data ingestion failed: {str(e)}")
            raise

    async def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process DataFrame data
        """
        # Add ingestion metadata
        df = df.copy()

        # Add ingestion tracking columns
        df.attrs['ingestion_id'] = str(uuid.uuid4())
        df.attrs['ingestion_timestamp'] = datetime.now().isoformat()
        df.attrs['ingestion_mode'] = self.ingestion_mode.value
        df.attrs['source_type'] = 'dataframe'

        # Update metrics
        self.metrics.update({
            'ingestion_mode': self.ingestion_mode.value,
            'data_format': 'dataframe',
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
            'ingestion_id': df.attrs['ingestion_id']
        })

        return df

    async def _ingest_from_file(self, file_path: Path) -> pd.DataFrame:
        """
        Ingest data from file source
        """
        try:
            # Detect format if enabled
            if self.format_detection:
                detected_format = await self._detect_format(file_path)
                logger.info(f"Detected format: {detected_format}")

            # Create data source
            from services.data_source_service import data_source_service
            self.data_source = await data_source_service.create_data_source_from_file(str(file_path))

            if not self.data_source:
                raise RuntimeError(f"Failed to create data source for file: {file_path}")

            # Get data based on ingestion mode
            if self.ingestion_mode == IngestionMode.STREAMING:
                df = await self._ingest_streaming()
            else:
                df = await self._ingest_batch()

            # Add ingestion metadata
            df.attrs['ingestion_id'] = str(uuid.uuid4())
            df.attrs['ingestion_timestamp'] = datetime.now().isoformat()
            df.attrs['ingestion_mode'] = self.ingestion_mode.value
            df.attrs['source_file'] = str(file_path)
            df.attrs['source_type'] = self.data_source.config.source_type

            # Update metrics
            self.metrics.update({
                'ingestion_mode': self.ingestion_mode.value,
                'data_format': self.data_source.config.source_type,
                'source_file': str(file_path),
                'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
                'ingestion_id': df.attrs['ingestion_id']
            })

            return df

        except Exception as e:
            logger.error(f"File ingestion failed: {str(e)}")
            raise
        finally:
            # Clean up data source
            if self.data_source:
                await self.data_source.disconnect()

    async def _detect_format(self, file_path: Path) -> DataFormat:
        """
        Detect file format
        """
        try:
            extension = file_path.suffix.lower()

            format_map = {
                '.csv': DataFormat.CSV,
                '.tsv': DataFormat.CSV,
                '.txt': DataFormat.CSV,
                '.xlsx': DataFormat.EXCEL,
                '.xls': DataFormat.EXCEL,
                '.xlsm': DataFormat.EXCEL,
                '.json': DataFormat.JSON,
                '.parquet': DataFormat.PARQUET
            }

            return format_map.get(extension, DataFormat.UNKNOWN)

        except Exception as e:
            logger.error(f"Format detection failed: {str(e)}")
            return DataFormat.UNKNOWN

    async def _ingest_batch(self) -> pd.DataFrame:
        """
        Batch ingestion - load all data at once
        """
        if not self.data_source:
            raise RuntimeError("Data source not initialized")
        return await self.data_source.get_data()

    async def _ingest_streaming(self) -> pd.DataFrame:
        """
        Streaming ingestion - load data in chunks
        """
        if not self.data_source:
            raise RuntimeError("Data source not initialized")

        chunks = []
        chunk_count = 0

        data_stream = await self.data_source.get_data_stream(chunk_size=self.chunk_size)
        async for chunk in data_stream:
            chunks.append(chunk)
            chunk_count += 1

            # Memory management
            current_memory = sum(chunk.memory_usage(deep=True).sum() for chunk in chunks) / 1024 / 1024
            if current_memory > self.max_memory_mb:
                logger.warning(f"Memory limit reached ({current_memory:.2f}MB), stopping ingestion")
                break

        if not chunks:
            raise RuntimeError("No data chunks ingested")

        # Combine all chunks
        result_df = pd.concat(chunks, ignore_index=True)

        # Update metrics
        self.metrics.update({
            'chunks_processed': chunk_count,
            'streaming_memory_limit_mb': self.max_memory_mb
        })

        return result_df


class DataFormatConverter:
    """
    Convert data between different formats
    """

    @staticmethod
    async def convert_to_dataframe(data: Any, source_format: DataFormat) -> pd.DataFrame:
        """
        Convert various data formats to DataFrame
        """
        try:
            if source_format == DataFormat.CSV:
                if isinstance(data, str):
                    return pd.read_csv(data)
                elif isinstance(data, pd.DataFrame):
                    return data
                else:
                    raise ValueError(f"Invalid data type for CSV: {type(data)}")

            elif source_format == DataFormat.EXCEL:
                if isinstance(data, str):
                    return pd.read_excel(data)
                elif isinstance(data, pd.DataFrame):
                    return data
                else:
                    raise ValueError(f"Invalid data type for Excel: {type(data)}")

            elif source_format == DataFormat.JSON:
                if isinstance(data, str):
                    return pd.read_json(data)
                elif isinstance(data, dict):
                    return pd.DataFrame(data)
                elif isinstance(data, list):
                    return pd.DataFrame(data)
                else:
                    raise ValueError(f"Invalid data type for JSON: {type(data)}")

            else:
                raise ValueError(f"Unsupported format: {source_format}")

        except Exception as e:
            logger.error(f"Format conversion failed: {str(e)}")
            raise

    @staticmethod
    async def detect_delimiter(file_path: Path) -> str:
        """
        Detect delimiter for text files
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(1024)

            # Common delimiters
            delimiters = [',', '\t', ';', '|', ':']
            delimiter_counts = {}

            for delimiter in delimiters:
                delimiter_counts[delimiter] = sample.count(delimiter)

            # Return most common delimiter
            if delimiter_counts:
                return max(delimiter_counts, key=lambda x: delimiter_counts[x])
            else:
                return ','  # Default to comma

        except Exception as e:
            logger.error(f"Delimiter detection failed: {str(e)}")
            return ','

    @staticmethod
    async def detect_encoding(file_path: Path) -> str:
        """
        Detect file encoding
        """
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(10000)

            # Try to detect encoding
            import chardet
            result = chardet.detect(sample)

            if result and result['encoding']:
                return result['encoding']
            else:
                return 'utf-8'  # Default to UTF-8

        except Exception as e:
            logger.error(f"Encoding detection failed: {str(e)}")
            return 'utf-8'


class IngestionMetrics:
    """
    Metrics collection for data ingestion
    """

    def __init__(self):
        self.metrics = {
            'total_ingestions': 0,
            'successful_ingestions': 0,
            'failed_ingestions': 0,
            'total_rows_ingested': 0,
            'total_memory_used_mb': 0,
            'avg_ingestion_time_seconds': 0,
            'ingestion_history': []
        }

    def record_ingestion(self,
                        ingestion_id: str,
                        success: bool,
                        rows_ingested: int,
                        memory_used_mb: float,
                        execution_time_seconds: float,
                        source_type: str,
                        error_message: Optional[str] = None):
        """
        Record ingestion metrics
        """
        self.metrics['total_ingestions'] += 1

        if success:
            self.metrics['successful_ingestions'] += 1
            self.metrics['total_rows_ingested'] += rows_ingested
            self.metrics['total_memory_used_mb'] += memory_used_mb

            # Update average ingestion time
            total_time = self.metrics['avg_ingestion_time_seconds'] * (self.metrics['successful_ingestions'] - 1)
            self.metrics['avg_ingestion_time_seconds'] = (total_time + execution_time_seconds) / self.metrics['successful_ingestions']
        else:
            self.metrics['failed_ingestions'] += 1

        # Record in history
        self.metrics['ingestion_history'].append({
            'ingestion_id': ingestion_id,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'rows_ingested': rows_ingested,
            'memory_used_mb': memory_used_mb,
            'execution_time_seconds': execution_time_seconds,
            'source_type': source_type,
            'error_message': error_message
        })

        # Keep only last 100 records
        if len(self.metrics['ingestion_history']) > 100:
            self.metrics['ingestion_history'] = self.metrics['ingestion_history'][-100:]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all ingestion metrics
        """
        return self.metrics.copy()

    def get_success_rate(self) -> float:
        """
        Get ingestion success rate
        """
        if self.metrics['total_ingestions'] == 0:
            return 0.0
        return (self.metrics['successful_ingestions'] / self.metrics['total_ingestions']) * 100

    def reset_metrics(self):
        """
        Reset all metrics
        """
        self.metrics = {
            'total_ingestions': 0,
            'successful_ingestions': 0,
            'failed_ingestions': 0,
            'total_rows_ingested': 0,
            'total_memory_used_mb': 0,
            'avg_ingestion_time_seconds': 0,
            'ingestion_history': []
        }


# Global metrics instance
ingestion_metrics = IngestionMetrics()
