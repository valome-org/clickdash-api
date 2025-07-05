"""
Universal Data Source Interface - Base classes for all data source implementations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
import pandas as pd
from pydantic import BaseModel, Field


class ConnectionStatus(Enum):
    """Status of data source connection"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    UNKNOWN = "unknown"


class DataSourceCapabilities(BaseModel):
    """Capabilities supported by a data source"""
    supports_streaming: bool = False
    supports_real_time: bool = False
    supports_pagination: bool = False
    supports_filtering: bool = False
    supports_aggregation: bool = False
    supports_joins: bool = False
    supports_schema_detection: bool = True
    supports_incremental_load: bool = False
    max_rows_per_request: Optional[int] = None
    supported_formats: List[str] = Field(default_factory=list)
    authentication_methods: List[str] = Field(default_factory=list)


class DataSourceConfig(BaseModel):
    """Configuration for a data source connection"""
    source_type: str
    name: str
    description: Optional[str] = None
    connection_params: Dict[str, Any] = Field(default_factory=dict)
    authentication: Optional[Dict[str, Any]] = None
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DataSourceMetadata(BaseModel):
    """Metadata about the data source"""
    source_id: str
    name: str
    description: Optional[str] = None
    data_schema: Optional[Dict[str, Any]] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    data_types: Dict[str, str] = Field(default_factory=dict)
    sample_data: Optional[Dict[str, Any]] = None
    last_updated: Optional[datetime] = None
    data_freshness: Optional[str] = None
    quality_score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class DataSourceInterface(ABC):
    """
    Universal interface that all data sources must implement

    This interface ensures all data sources provide consistent functionality
    regardless of their underlying implementation (Excel, CSV, API, Database, etc.)
    """

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.connection_status = ConnectionStatus.UNKNOWN
        self.last_error: Optional[str] = None
        self.metadata: Optional[DataSourceMetadata] = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the data source

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection to the data source

        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the connection is working

        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    async def get_capabilities(self) -> DataSourceCapabilities:
        """
        Get the capabilities of this data source

        Returns:
            DataSourceCapabilities: Supported features and limitations
        """
        pass

    @abstractmethod
    async def get_metadata(self) -> DataSourceMetadata:
        """
        Extract metadata about the data source

        Returns:
            DataSourceMetadata: Information about the data structure and content
        """
        pass

    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """
        Get the schema/structure of the data

        Returns:
            Dict[str, Any]: Schema information including column names, types, etc.
        """
        pass

    @abstractmethod
    async def get_sample_data(self, limit: int = 10) -> pd.DataFrame:
        """
        Get a sample of the data for preview

        Args:
            limit (int): Number of rows to return

        Returns:
            pd.DataFrame: Sample data
        """
        pass

    @abstractmethod
    async def get_data(self,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None,
                      filters: Optional[Dict[str, Any]] = None,
                      columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get data from the source with optional filtering and pagination

        Args:
            limit (Optional[int]): Maximum number of rows to return
            offset (Optional[int]): Number of rows to skip
            filters (Optional[Dict[str, Any]]): Filtering criteria
            columns (Optional[List[str]]): Specific columns to return

        Returns:
            pd.DataFrame: The requested data
        """
        pass

    @abstractmethod
    async def get_data_stream(self,
                            chunk_size: int = 1000,
                            filters: Optional[Dict[str, Any]] = None) -> AsyncGenerator[pd.DataFrame, None]:
        """
        Get data as a stream for large datasets

        Args:
            chunk_size (int): Size of each data chunk
            filters (Optional[Dict[str, Any]]): Filtering criteria

        Yields:
            pd.DataFrame: Chunks of data
        """
        pass

    @abstractmethod
    async def validate_data(self) -> Dict[str, Any]:
        """
        Validate the data quality and structure

        Returns:
            Dict[str, Any]: Validation results including errors, warnings, and quality metrics
        """
        pass

    # Common utility methods

    def get_connection_status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self.connection_status

    def get_last_error(self) -> Optional[str]:
        """Get the last error message"""
        return self.last_error

    def set_error(self, error: str):
        """Set error message and update status"""
        self.last_error = error
        self.connection_status = ConnectionStatus.ERROR

    def clear_error(self):
        """Clear error state"""
        self.last_error = None

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            is_connected = await self.test_connection()
            capabilities = await self.get_capabilities()
            metadata = await self.get_metadata() if is_connected else None

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connection_status": self.connection_status.value,
                "capabilities": capabilities.dict() if capabilities else None,
                "metadata": metadata.dict() if metadata else None,
                "last_error": self.last_error,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.set_error(str(e))
            return {
                "status": "unhealthy",
                "connection_status": self.connection_status.value,
                "last_error": str(e),
                "timestamp": datetime.now().isoformat()
            }
