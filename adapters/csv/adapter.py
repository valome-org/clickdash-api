"""
CSV Data Source Adapter - Implementation for CSV file data sources
"""

import uuid
import chardet
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
import pandas as pd
import numpy as np
from core.data_sources.base import (
    DataSourceInterface,
    DataSourceConfig,
    DataSourceCapabilities,
    DataSourceMetadata,
    ConnectionStatus
)
from utils.serialization import make_json_serializable
import logging

logger = logging.getLogger(__name__)


class CSVAdapter(DataSourceInterface):
    """
    CSV file data source adapter

    Handles CSV files with automatic encoding detection and flexible parsing
    """

    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.file_path: Optional[Path] = None
        self.df: Optional[pd.DataFrame] = None
        self.encoding: Optional[str] = None
        self.delimiter: str = ','
        self.supported_extensions = ['.csv', '.tsv', '.txt']

    async def connect(self) -> bool:
        """
        Connect to CSV file (load and validate)
        """
        try:
            self.connection_status = ConnectionStatus.CONNECTING
            self.clear_error()

            # Get file path from connection parameters
            file_path = self.config.connection_params.get('file_path')
            if not file_path:
                self.set_error("No file_path provided in connection parameters")
                return False

            self.file_path = Path(file_path)

            # Validate file exists
            if not self.file_path.exists():
                self.set_error(f"CSV file not found: {self.file_path}")
                return False

            # Validate file extension
            if self.file_path.suffix.lower() not in self.supported_extensions:
                self.set_error(f"Unsupported file extension: {self.file_path.suffix}")
                return False

            # Detect encoding
            self.encoding = await self._detect_encoding()
            logger.info(f"Detected encoding: {self.encoding}")

            # Get delimiter from config or detect
            self.delimiter = self.config.connection_params.get('delimiter', ',')
            if self.delimiter == 'auto':
                self.delimiter = await self._detect_delimiter()
                logger.info(f"Detected delimiter: {repr(self.delimiter)}")

            # Load CSV file
            self.df = pd.read_csv(
                self.file_path,
                encoding=self.encoding,
                delimiter=self.delimiter,
                engine='python',  # More flexible parsing
                skipinitialspace=True,
                na_values=['', 'null', 'NULL', 'N/A', 'n/a', 'NA', 'na'],
                keep_default_na=True
            )

            # Validate data
            if self.df is None or self.df.empty:
                self.set_error("CSV file is empty or could not be read")
                return False

            # Clean column names
            self.df.columns = self.df.columns.str.strip()

            # Extract metadata
            self.metadata = await self._extract_metadata()

            self.connection_status = ConnectionStatus.CONNECTED
            logger.info(f"Successfully connected to CSV file: {self.file_path}")
            return True

        except Exception as e:
            self.set_error(f"Failed to connect to CSV file: {str(e)}")
            logger.error(f"CSV connection error: {str(e)}")
            return False

    async def _detect_encoding(self) -> str:
        """
        Detect the encoding of the CSV file
        """
        try:
            with open(self.file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                confidence = result.get('confidence', 0)
                detected_encoding = result.get('encoding', 'utf-8')

                # Use utf-8 as fallback if confidence is low
                if confidence < 0.7:
                    logger.warning(f"Low confidence ({confidence}) for detected encoding {detected_encoding}, using utf-8")
                    return 'utf-8'

                return detected_encoding

        except Exception as e:
            logger.warning(f"Encoding detection failed: {str(e)}, using utf-8")
            return 'utf-8'

    async def _detect_delimiter(self) -> str:
        """
        Detect the delimiter of the CSV file
        """
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                # Read first few lines
                sample = f.read(1024)

            # Try different delimiters
            delimiters = [',', ';', '\t', '|', ':']
            delimiter_counts = {}

            for delim in delimiters:
                delimiter_counts[delim] = sample.count(delim)

            # Return delimiter with highest count
            best_delimiter = max(delimiter_counts, key=delimiter_counts.get)

            if delimiter_counts[best_delimiter] == 0:
                logger.warning("No common delimiters found, using comma")
                return ','

            return best_delimiter

        except Exception as e:
            logger.warning(f"Delimiter detection failed: {str(e)}, using comma")
            return ','

    async def disconnect(self) -> bool:
        """
        Disconnect from CSV file (cleanup)
        """
        try:
            self.df = None
            self.metadata = None
            self.connection_status = ConnectionStatus.DISCONNECTED
            logger.info(f"Disconnected from CSV file: {self.file_path}")
            return True

        except Exception as e:
            self.set_error(f"Failed to disconnect: {str(e)}")
            return False

    async def test_connection(self) -> bool:
        """
        Test if CSV file is accessible and readable
        """
        try:
            if not self.file_path or not self.file_path.exists():
                return False

            # Try to read a small sample
            test_df = pd.read_csv(
                self.file_path,
                encoding=self.encoding or 'utf-8',
                delimiter=self.delimiter,
                nrows=1
            )
            return test_df is not None and not test_df.empty

        except Exception as e:
            self.set_error(f"Connection test failed: {str(e)}")
            return False

    async def get_capabilities(self) -> DataSourceCapabilities:
        """
        Get CSV adapter capabilities
        """
        return DataSourceCapabilities(
            supports_streaming=True,
            supports_real_time=False,
            supports_pagination=True,
            supports_filtering=True,
            supports_aggregation=False,
            supports_joins=False,
            supports_schema_detection=True,
            supports_incremental_load=False,
            max_rows_per_request=1000000,
            supported_formats=['csv', 'tsv', 'txt'],
            authentication_methods=[]
        )

    async def get_metadata(self) -> DataSourceMetadata:
        """
        Get metadata about the CSV file
        """
        if self.metadata:
            return self.metadata

        return await self._extract_metadata()

    async def _extract_metadata(self) -> DataSourceMetadata:
        """
        Extract comprehensive metadata from CSV file
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call connect() first.")

        # Basic statistics
        row_count = len(self.df)
        column_count = len(self.df.columns)

        # Data types
        data_types = {}
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if dtype.startswith('int'):
                data_types[col] = 'integer'
            elif dtype.startswith('float'):
                data_types[col] = 'float'
            elif dtype.startswith('bool'):
                data_types[col] = 'boolean'
            elif dtype.startswith('datetime'):
                data_types[col] = 'datetime'
            else:
                data_types[col] = 'string'

        # Sample data
        sample_data = make_json_serializable(self.df.head(5).to_dict())

        # Schema information
        schema = {
            'columns': list(self.df.columns),
            'dtypes': data_types,
            'nullable_columns': [col for col in self.df.columns if self.df[col].isnull().any()],
            'numeric_columns': list(self.df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': list(self.df.select_dtypes(include=['object']).columns),
            'datetime_columns': list(self.df.select_dtypes(include=['datetime']).columns),
            'encoding': self.encoding,
            'delimiter': self.delimiter
        }

        # File information
        file_stats = self.file_path.stat()

        return DataSourceMetadata(
            source_id=str(uuid.uuid4()),
            name=self.file_path.name,
            description=f"CSV file: {self.file_path.name}",
            schema=schema,
            row_count=row_count,
            column_count=column_count,
            data_types=data_types,
            sample_data=sample_data,
            last_updated=datetime.fromtimestamp(file_stats.st_mtime),
            data_freshness="static",
            quality_score=await self._calculate_quality_score(),
            tags=['csv', 'file', 'tabular']
        )

    async def _calculate_quality_score(self) -> float:
        """
        Calculate data quality score (0-100)
        """
        if self.df is None:
            return 0.0

        total_cells = self.df.size
        if total_cells == 0:
            return 0.0

        # Count missing values
        missing_cells = self.df.isnull().sum().sum()
        completeness_score = ((total_cells - missing_cells) / total_cells) * 100

        # Check for duplicate rows
        duplicates = self.df.duplicated().sum()
        uniqueness_score = ((len(self.df) - duplicates) / len(self.df)) * 100

        # Basic validity check (non-empty columns)
        valid_columns = sum(1 for col in self.df.columns if not self.df[col].empty)
        validity_score = (valid_columns / len(self.df.columns)) * 100

        # Check for consistent data types
        consistency_score = 100.0  # Default full score
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                # Check if numeric-looking strings are consistently formatted
                non_null_values = self.df[col].dropna()
                if len(non_null_values) > 0:
                    # Simple check for mixed types
                    sample_values = non_null_values.head(100)
                    numeric_count = sum(1 for v in sample_values if str(v).replace('.', '').replace('-', '').isdigit())
                    if 0 < numeric_count < len(sample_values):
                        consistency_score -= 5  # Penalty for mixed types

        # Weighted average
        quality_score = (
            completeness_score * 0.4 +
            uniqueness_score * 0.3 +
            validity_score * 0.2 +
            consistency_score * 0.1
        )

        return round(quality_score, 2)

    async def get_schema(self) -> Dict[str, Any]:
        """
        Get the schema of the CSV data
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call connect() first.")

        metadata = await self.get_metadata()
        return metadata.schema

    async def get_sample_data(self, limit: int = 10) -> pd.DataFrame:
        """
        Get sample data from CSV file
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call connect() first.")

        return self.df.head(limit)

    async def get_data(self,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None,
                      filters: Optional[Dict[str, Any]] = None,
                      columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get data from CSV file with optional filtering and pagination
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call connect() first.")

        result_df = self.df.copy()

        # Apply column filtering
        if columns:
            available_columns = [col for col in columns if col in result_df.columns]
            if available_columns:
                result_df = result_df[available_columns]
            else:
                raise ValueError(f"None of the specified columns found in data: {columns}")

        # Apply filters
        if filters:
            result_df = self._apply_filters(result_df, filters)

        # Apply pagination
        if offset is not None:
            result_df = result_df.iloc[offset:]

        if limit is not None:
            result_df = result_df.head(limit)

        return result_df

    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply filters to DataFrame
        """
        for column, filter_value in filters.items():
            if column not in df.columns:
                continue

            if isinstance(filter_value, dict):
                # Handle complex filters
                if 'equals' in filter_value:
                    df = df[df[column] == filter_value['equals']]
                elif 'not_equals' in filter_value:
                    df = df[df[column] != filter_value['not_equals']]
                elif 'contains' in filter_value:
                    df = df[df[column].astype(str).str.contains(filter_value['contains'], na=False)]
                elif 'greater_than' in filter_value:
                    df = df[df[column] > filter_value['greater_than']]
                elif 'less_than' in filter_value:
                    df = df[df[column] < filter_value['less_than']]
                elif 'in' in filter_value:
                    df = df[df[column].isin(filter_value['in'])]
            else:
                # Simple equality filter
                df = df[df[column] == filter_value]

        return df

    async def get_data_stream(self,
                            chunk_size: int = 1000,
                            filters: Optional[Dict[str, Any]] = None) -> AsyncGenerator[pd.DataFrame, None]:
        """
        Get data as a stream for large CSV files
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call connect() first.")

        # Apply filters if provided
        data_df = self.df
        if filters:
            data_df = self._apply_filters(data_df, filters)

        # Yield chunks
        for i in range(0, len(data_df), chunk_size):
            chunk = data_df.iloc[i:i + chunk_size]
            yield chunk

    async def validate_data(self) -> Dict[str, Any]:
        """
        Validate CSV data quality and structure
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call connect() first.")

        validation_results = {
            'status': 'valid',
            'errors': [],
            'warnings': [],
            'metrics': {},
            'recommendations': []
        }

        # Check for empty data
        if self.df.empty:
            validation_results['errors'].append("Data is empty")
            validation_results['status'] = 'invalid'
            return validation_results

        # Check for missing values
        missing_values = self.df.isnull().sum()
        high_missing_columns = missing_values[missing_values > len(self.df) * 0.5].index.tolist()

        if high_missing_columns:
            validation_results['warnings'].append(
                f"Columns with >50% missing values: {high_missing_columns}"
            )
            validation_results['recommendations'].append(
                "Consider removing or imputing high-missing columns"
            )

        # Check for duplicate rows
        duplicates = self.df.duplicated().sum()
        if duplicates > 0:
            validation_results['warnings'].append(f"Found {duplicates} duplicate rows")
            validation_results['recommendations'].append("Consider removing duplicate rows")

        # Check for empty columns
        empty_columns = [col for col in self.df.columns if self.df[col].isnull().all()]
        if empty_columns:
            validation_results['warnings'].append(f"Empty columns found: {empty_columns}")
            validation_results['recommendations'].append("Consider removing empty columns")

        # Check for encoding issues
        if self.encoding and self.encoding.lower() != 'utf-8':
            validation_results['warnings'].append(f"File uses {self.encoding} encoding instead of UTF-8")
            validation_results['recommendations'].append("Consider converting to UTF-8 for better compatibility")

        # Data quality metrics
        validation_results['metrics'] = {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'missing_values_count': int(missing_values.sum()),
            'missing_values_percentage': round((missing_values.sum() / self.df.size) * 100, 2),
            'duplicate_rows': int(duplicates),
            'empty_columns': len(empty_columns),
            'encoding': self.encoding,
            'delimiter': self.delimiter,
            'quality_score': await self._calculate_quality_score()
        }

        # Set final status
        if validation_results['errors']:
            validation_results['status'] = 'invalid'
        elif validation_results['warnings']:
            validation_results['status'] = 'valid_with_warnings'
        else:
            validation_results['status'] = 'valid'

        return validation_results
