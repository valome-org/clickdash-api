"""
Data sources package for universal data source management
Contains interfaces and registry for all data source types
"""

from .base import DataSourceInterface, DataSourceConfig, DataSourceCapabilities, ConnectionStatus
from .registry import DataSourceRegistry

__all__ = [
    'DataSourceInterface',
    'DataSourceConfig',
    'DataSourceCapabilities',
    'ConnectionStatus',
    'DataSourceRegistry'
]
