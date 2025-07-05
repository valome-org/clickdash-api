"""
Data Source Management Service
Integrates the new data source architecture with the existing system
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from core.data_sources.registry import data_source_registry
from core.data_sources.base import DataSourceConfig, DataSourceInterface
from adapters.excel.adapter import ExcelAdapter
from adapters.csv.adapter import CSVAdapter
import pandas as pd

logger = logging.getLogger(__name__)


class DataSourceService:
    """
    Service for managing data sources using the new architecture
    """

    def __init__(self):
        self.registry = data_source_registry
        self._initialize_adapters()

    def _initialize_adapters(self):
        """Initialize and register all available data source adapters"""
        try:
            # Register Excel adapter
            self.registry.register_source(
                source_type="excel",
                source_class=ExcelAdapter,
                metadata={
                    "name": "Excel File Adapter",
                    "description": "Handles Excel files (.xlsx, .xls, .xlsm)",
                    "supported_formats": ["xlsx", "xls", "xlsm"],
                    "category": "file"
                }
            )

            # Register CSV adapter
            self.registry.register_source(
                source_type="csv",
                source_class=CSVAdapter,
                metadata={
                    "name": "CSV File Adapter",
                    "description": "Handles CSV files with automatic encoding detection",
                    "supported_formats": ["csv", "tsv", "txt"],
                    "category": "file"
                }
            )

            logger.info("Successfully initialized data source adapters")

        except Exception as e:
            logger.error(f"Failed to initialize adapters: {str(e)}")
            raise

    async def create_data_source_from_file(self,
                                         file_path: str,
                                         source_name: Optional[str] = None,
                                         **kwargs) -> Optional[DataSourceInterface]:
        """
        Create a data source from a file path

        Args:
            file_path: Path to the data file
            source_name: Optional name for the data source
            **kwargs: Additional configuration parameters

        Returns:
            DataSourceInterface: Created data source instance
        """
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                logger.error(f"File not found: {file_path}")
                return None

            # Determine source type from file extension
            extension = file_path_obj.suffix.lower()

            if extension in ['.xlsx', '.xls', '.xlsm']:
                source_type = "excel"
            elif extension in ['.csv', '.tsv', '.txt']:
                source_type = "csv"
            else:
                logger.error(f"Unsupported file type: {extension}")
                return None

            # Create configuration
            config = DataSourceConfig(
                source_type=source_type,
                name=source_name or file_path_obj.stem,
                description=f"Auto-created from {file_path}",
                connection_params={
                    'file_path': str(file_path_obj),
                    **kwargs
                }
            )

            # Create and connect data source
            data_source = await self.registry.create_source(config)

            if data_source:
                success = await data_source.connect()
                if success:
                    logger.info(f"Successfully created data source: {config.name}")
                    return data_source
                else:
                    logger.error(f"Failed to connect to data source: {config.name}")
                    return None
            else:
                logger.error(f"Failed to create data source: {config.name}")
                return None

        except Exception as e:
            logger.error(f"Error creating data source from file: {str(e)}")
            return None

    async def get_data_from_file(self,
                               file_path: str,
                               limit: Optional[int] = None,
                               **kwargs) -> Optional[pd.DataFrame]:
        """
        Get data from a file using the appropriate adapter

        Args:
            file_path: Path to the data file
            limit: Optional limit on number of rows
            **kwargs: Additional parameters

        Returns:
            pd.DataFrame: Data from the file
        """
        try:
            # Create temporary data source
            data_source = await self.create_data_source_from_file(file_path, **kwargs)

            if not data_source:
                return None

            # Get data
            data = await data_source.get_data(limit=limit)

            # Cleanup
            await data_source.disconnect()

            return data

        except Exception as e:
            logger.error(f"Error getting data from file: {str(e)}")
            return None

    async def analyze_file(self, file_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Analyze a file and return comprehensive metadata and quality information

        Args:
            file_path: Path to the data file
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Create temporary data source
            data_source = await self.create_data_source_from_file(file_path, **kwargs)

            if not data_source:
                return None

            # Get metadata and validation results
            metadata = await data_source.get_metadata()
            validation_results = await data_source.validate_data()
            capabilities = await data_source.get_capabilities()

            # Cleanup
            await data_source.disconnect()

            return {
                "metadata": metadata.dict(),
                "validation": validation_results,
                "capabilities": capabilities.dict(),
                "source_type": data_source.config.source_type
            }

        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            return None

    def get_supported_formats(self) -> List[str]:
        """
        Get all supported file formats

        Returns:
            List[str]: List of supported file extensions
        """
        supported_formats = []

        for source_type in self.registry.get_registered_sources():
            metadata = self.registry.get_source_metadata(source_type)
            if metadata and "supported_formats" in metadata:
                supported_formats.extend(metadata["supported_formats"])

        return list(set(supported_formats))

    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get information about the data source registry

        Returns:
            Dict[str, Any]: Registry information
        """
        return self.registry.get_registry_info()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the data source service

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            registry_info = self.get_registry_info()
            supported_formats = self.get_supported_formats()

            return {
                "status": "healthy",
                "registry_info": registry_info,
                "supported_formats": supported_formats,
                "timestamp": pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": pd.Timestamp.now().isoformat()
            }


# Global instance
data_source_service = DataSourceService()
