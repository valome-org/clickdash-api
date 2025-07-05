"""
Data Source Registry - Centralized management of all data sources
"""

from typing import Dict, List, Optional, Type, Any
from datetime import datetime
import logging
from .base import DataSourceInterface, DataSourceConfig, DataSourceCapabilities, ConnectionStatus

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    """
    Centralized registry for managing all data source implementations

    This registry allows for dynamic discovery and management of data sources,
    making it easy to add new data source types without modifying core code.
    """

    def __init__(self):
        self._registered_sources: Dict[str, Type[DataSourceInterface]] = {}
        self._active_connections: Dict[str, DataSourceInterface] = {}
        self._source_metadata: Dict[str, Dict[str, Any]] = {}

    def register_source(self,
                       source_type: str,
                       source_class: Type[DataSourceInterface],
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a new data source type

        Args:
            source_type (str): Unique identifier for the data source type
            source_class (Type[DataSourceInterface]): The data source implementation class
            metadata (Optional[Dict[str, Any]]): Additional metadata about the source

        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            # Validate that the class implements the interface
            if not issubclass(source_class, DataSourceInterface):
                raise ValueError(f"Source class must implement DataSourceInterface")

            # Check if source type already exists
            if source_type in self._registered_sources:
                logger.warning(f"Data source type '{source_type}' already registered. Overwriting.")

            self._registered_sources[source_type] = source_class
            self._source_metadata[source_type] = metadata or {}

            logger.info(f"Successfully registered data source type: {source_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to register data source type '{source_type}': {str(e)}")
            return False

    async def unregister_source(self, source_type: str) -> bool:
        """
        Unregister a data source type

        Args:
            source_type (str): The source type to unregister

        Returns:
            bool: True if unregistration successful, False otherwise
        """
        try:
            if source_type not in self._registered_sources:
                logger.warning(f"Data source type '{source_type}' not found for unregistration")
                return False

            # Close any active connections of this type
            connections_to_close = [
                conn_id for conn_id, conn in self._active_connections.items()
                if conn.config.source_type == source_type
            ]

            for conn_id in connections_to_close:
                await self.disconnect_source(conn_id)

            # Remove from registry
            del self._registered_sources[source_type]
            if source_type in self._source_metadata:
                del self._source_metadata[source_type]

            logger.info(f"Successfully unregistered data source type: {source_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister data source type '{source_type}': {str(e)}")
            return False

    def get_registered_sources(self) -> List[str]:
        """
        Get list of all registered data source types

        Returns:
            List[str]: List of registered source type names
        """
        return list(self._registered_sources.keys())

    def get_source_metadata(self, source_type: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific source type

        Args:
            source_type (str): The source type to get metadata for

        Returns:
            Optional[Dict[str, Any]]: Source metadata or None if not found
        """
        return self._source_metadata.get(source_type)

    def is_source_registered(self, source_type: str) -> bool:
        """
        Check if a source type is registered

        Args:
            source_type (str): The source type to check

        Returns:
            bool: True if registered, False otherwise
        """
        return source_type in self._registered_sources

    async def create_source(self, config: DataSourceConfig) -> Optional[DataSourceInterface]:
        """
        Create a new data source instance

        Args:
            config (DataSourceConfig): Configuration for the data source

        Returns:
            Optional[DataSourceInterface]: Created data source instance or None if failed
        """
        try:
            source_type = config.source_type

            if source_type not in self._registered_sources:
                logger.error(f"Unknown data source type: {source_type}")
                return None

            source_class = self._registered_sources[source_type]
            source_instance = source_class(config)

            # Generate unique connection ID
            connection_id = f"{source_type}_{config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Store the active connection
            self._active_connections[connection_id] = source_instance

            logger.info(f"Created data source instance: {connection_id}")
            return source_instance

        except Exception as e:
            logger.error(f"Failed to create data source for type '{config.source_type}': {str(e)}")
            return None

    async def connect_source(self, connection_id: str) -> bool:
        """
        Connect to a data source

        Args:
            connection_id (str): ID of the connection to establish

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if connection_id not in self._active_connections:
                logger.error(f"Connection ID not found: {connection_id}")
                return False

            source = self._active_connections[connection_id]
            success = await source.connect()

            if success:
                logger.info(f"Successfully connected to data source: {connection_id}")
            else:
                logger.error(f"Failed to connect to data source: {connection_id}")

            return success

        except Exception as e:
            logger.error(f"Error connecting to data source '{connection_id}': {str(e)}")
            return False

    async def disconnect_source(self, connection_id: str) -> bool:
        """
        Disconnect from a data source

        Args:
            connection_id (str): ID of the connection to close

        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if connection_id not in self._active_connections:
                logger.error(f"Connection ID not found: {connection_id}")
                return False

            source = self._active_connections[connection_id]
            success = await source.disconnect()

            # Remove from active connections
            del self._active_connections[connection_id]

            if success:
                logger.info(f"Successfully disconnected from data source: {connection_id}")
            else:
                logger.error(f"Failed to disconnect from data source: {connection_id}")

            return success

        except Exception as e:
            logger.error(f"Error disconnecting from data source '{connection_id}': {str(e)}")
            return False

    def get_active_connections(self) -> List[str]:
        """
        Get list of active connection IDs

        Returns:
            List[str]: List of active connection IDs
        """
        return list(self._active_connections.keys())

    def get_connection(self, connection_id: str) -> Optional[DataSourceInterface]:
        """
        Get a specific active connection

        Args:
            connection_id (str): ID of the connection to retrieve

        Returns:
            Optional[DataSourceInterface]: The connection instance or None if not found
        """
        return self._active_connections.get(connection_id)

    async def get_connection_status(self, connection_id: str) -> ConnectionStatus:
        """
        Get the status of a specific connection

        Args:
            connection_id (str): ID of the connection to check

        Returns:
            ConnectionStatus: Current connection status
        """
        if connection_id not in self._active_connections:
            return ConnectionStatus.UNKNOWN

        source = self._active_connections[connection_id]
        return source.get_connection_status()

    async def test_connection(self, connection_id: str) -> bool:
        """
        Test a specific connection

        Args:
            connection_id (str): ID of the connection to test

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if connection_id not in self._active_connections:
            return False

        source = self._active_connections[connection_id]
        return await source.test_connection()

    async def get_source_capabilities(self, source_type: str) -> Optional[DataSourceCapabilities]:
        """
        Get capabilities for a specific source type

        Args:
            source_type (str): The source type to get capabilities for

        Returns:
            Optional[DataSourceCapabilities]: Capabilities or None if not available
        """
        if source_type not in self._registered_sources:
            return None

        try:
            # Create a temporary instance to get capabilities
            source_class = self._registered_sources[source_type]
            temp_config = DataSourceConfig(
                source_type=source_type,
                name="temp_for_capabilities"
            )
            temp_instance = source_class(temp_config)

            return await temp_instance.get_capabilities()

        except Exception as e:
            logger.error(f"Failed to get capabilities for source type '{source_type}': {str(e)}")
            return None

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health check on all active connections

        Returns:
            Dict[str, Any]: Health check results for all connections
        """
        results = {}

        for connection_id, source in self._active_connections.items():
            try:
                health_result = await source.health_check()
                results[connection_id] = health_result
            except Exception as e:
                results[connection_id] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        return {
            "overall_status": "healthy" if all(r.get("status") == "healthy" for r in results.values()) else "unhealthy",
            "total_connections": len(self._active_connections),
            "healthy_connections": len([r for r in results.values() if r.get("status") == "healthy"]),
            "connections": results,
            "timestamp": datetime.now().isoformat()
        }

    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the registry

        Returns:
            Dict[str, Any]: Registry information
        """
        return {
            "registered_sources": list(self._registered_sources.keys()),
            "active_connections": len(self._active_connections),
            "source_metadata": self._source_metadata,
            "connection_ids": list(self._active_connections.keys()),
            "timestamp": datetime.now().isoformat()
        }


# Global registry instance
data_source_registry = DataSourceRegistry()
