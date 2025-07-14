"""
Core dashboard generation system.

This module provides comprehensive dashboard generation capabilities including:
- Dynamic dashboard builder
- Template-based generation
- Export and integration systems
- Version control and updates
"""

# Import base classes first
from .base import (
    DashboardTemplate,
    LayoutEngine,
    ComponentPlacement,
    RenderingContext
)

# Import dashboard builder components
try:
    from .dashboard_builder import (
        DashboardBuilder,
        DashboardGenerationRequest,
        DashboardGenerationResult,
        ComponentRenderer
    )
except ImportError:
    pass

# Import export system components
try:
    from .export_system import (
        ExportManager,
        ExportRequest,
        ExportResult,
        ExportFormat,
        EmbeddingGenerator
    )
except ImportError:
    pass

# Import version control components
try:
    from .version_control import (
        VersionManager,
        DashboardVersion,
        ChangeTracker,
        UpdateNotifier
    )
except ImportError:
    pass

__all__ = [
    # Base dashboard components
    "DashboardTemplate",
    "LayoutEngine",
    "ComponentPlacement",
    "RenderingContext",

    # Dashboard builder
    "DashboardBuilder",
    "DashboardGenerationRequest",
    "DashboardGenerationResult",
    "ComponentRenderer",

    # Export system
    "ExportManager",
    "ExportRequest",
    "ExportResult",
    "ExportFormat",
    "EmbeddingGenerator",

    # Version control
    "VersionManager",
    "DashboardVersion",
    "ChangeTracker",
    "UpdateNotifier"
]
