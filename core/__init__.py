"""
Core package for AI Dashboard Platform
Contains universal interfaces and base classes for data processing
"""

from .data_sources.base import DataSourceInterface, DataSourceConfig, DataSourceCapabilities
from .data_sources.registry import DataSourceRegistry
from .pipeline.base import DataPipeline

__all__ = [
    'DataSourceInterface',
    'DataSourceConfig',
    'DataSourceCapabilities',
    'DataSourceRegistry',
    'DataPipeline'
]
