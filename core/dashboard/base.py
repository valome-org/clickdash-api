"""
Base dashboard generation components.

This module defines the fundamental interfaces and classes for:
- Dashboard templates and layouts
- Component placement and rendering
- Layout optimization and responsive design
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class ComponentType(str, Enum):
    """Types of dashboard components."""
    CHART = "chart"
    METRIC = "metric"
    TABLE = "table"
    TEXT = "text"
    IMAGE = "image"
    FILTER = "filter"
    HEADER = "header"
    FOOTER = "footer"
    SPACER = "spacer"
    CONTAINER = "container"


class LayoutType(str, Enum):
    """Dashboard layout types."""
    GRID = "grid"
    FLOW = "flow"
    FIXED = "fixed"
    RESPONSIVE = "responsive"
    DASHBOARD = "dashboard"
    REPORT = "report"


class ResponsiveBreakpoint(str, Enum):
    """Responsive design breakpoints."""
    MOBILE = "mobile"      # < 768px
    TABLET = "tablet"      # 768px - 1024px
    DESKTOP = "desktop"    # 1024px - 1440px
    LARGE = "large"        # > 1440px


class ComponentPlacement(BaseModel):
    """Defines where and how a component is placed in a layout."""

    component_id: str = Field(..., description="Unique component identifier")
    component_type: ComponentType = Field(..., description="Type of component")

    # Grid positioning
    grid_x: int = Field(default=0, description="Grid column position")
    grid_y: int = Field(default=0, description="Grid row position")
    grid_width: int = Field(default=1, description="Grid columns span")
    grid_height: int = Field(default=1, description="Grid rows span")

    # Absolute positioning (optional)
    absolute_x: Optional[float] = Field(None, description="Absolute X position (px)")
    absolute_y: Optional[float] = Field(None, description="Absolute Y position (px)")
    absolute_width: Optional[float] = Field(None, description="Absolute width (px)")
    absolute_height: Optional[float] = Field(None, description="Absolute height (px)")

    # Layout constraints
    min_width: Optional[int] = Field(None, description="Minimum width (grid units)")
    min_height: Optional[int] = Field(None, description="Minimum height (grid units)")
    max_width: Optional[int] = Field(None, description="Maximum width (grid units)")
    max_height: Optional[int] = Field(None, description="Maximum height (grid units)")

    # Responsive behavior
    responsive_config: Dict[ResponsiveBreakpoint, Dict[str, Any]] = Field(
        default_factory=dict, description="Responsive configuration per breakpoint"
    )

    # Visual properties
    z_index: int = Field(default=0, description="Stacking order")
    margin: Dict[str, int] = Field(default_factory=lambda: {"top": 0, "right": 0, "bottom": 0, "left": 0})
    padding: Dict[str, int] = Field(default_factory=lambda: {"top": 0, "right": 0, "bottom": 0, "left": 0})

    # Component-specific configuration
    component_config: Dict[str, Any] = Field(default_factory=dict, description="Component-specific settings")
    style_overrides: Dict[str, Any] = Field(default_factory=dict, description="CSS style overrides")


class DashboardTemplate(BaseModel):
    """Template for dashboard layout and styling."""

    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")

    # Layout configuration
    layout_type: LayoutType = Field(default=LayoutType.GRID)
    grid_columns: int = Field(default=12, description="Number of grid columns")
    grid_rows: int = Field(default=8, description="Number of grid rows")
    grid_gap: int = Field(default=16, description="Gap between grid items (px)")

    # Responsive configuration
    responsive_enabled: bool = Field(default=True, description="Enable responsive design")
    breakpoint_configs: Dict[ResponsiveBreakpoint, Dict[str, Any]] = Field(
        default_factory=dict, description="Configuration per breakpoint"
    )

    # Styling
    theme: str = Field(default="default", description="Visual theme")
    color_scheme: str = Field(default="primary", description="Color scheme")
    font_family: str = Field(default="Inter, sans-serif", description="Primary font family")

    # Container styling
    background_color: str = Field(default="#ffffff", description="Background color")
    container_max_width: Optional[str] = Field(None, description="Maximum container width")
    container_padding: Dict[str, int] = Field(
        default_factory=lambda: {"top": 24, "right": 24, "bottom": 24, "left": 24}
    )

    # Component defaults
    default_component_styles: Dict[ComponentType, Dict[str, Any]] = Field(
        default_factory=dict, description="Default styles per component type"
    )

    # Template metadata
    category: str = Field(default="general", description="Template category")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    use_count: int = Field(default=0, description="Usage counter")

    # Performance characteristics
    estimated_load_time: float = Field(default=2.0, description="Estimated load time (seconds)")
    complexity_score: float = Field(default=0.5, description="Template complexity (0-1)")
    mobile_optimized: bool = Field(default=True, description="Mobile optimization status")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class RenderingContext(BaseModel):
    """Context for rendering dashboard components."""

    # Target environment
    output_format: str = Field(default="html", description="Output format (html, pdf, png, etc.)")
    target_width: int = Field(default=1200, description="Target width (px)")
    target_height: int = Field(default=800, description="Target height (px)")
    device_type: ResponsiveBreakpoint = Field(default=ResponsiveBreakpoint.DESKTOP)

    # Rendering options
    interactive: bool = Field(default=True, description="Enable interactive features")
    animations: bool = Field(default=True, description="Enable animations")
    high_dpi: bool = Field(default=False, description="High DPI rendering")
    print_friendly: bool = Field(default=False, description="Print-friendly styling")

    # Performance options
    lazy_loading: bool = Field(default=True, description="Enable lazy loading")
    data_sampling: bool = Field(default=False, description="Enable data sampling for large datasets")
    max_data_points: int = Field(default=10000, description="Maximum data points per chart")

    # Accessibility options
    accessibility_enabled: bool = Field(default=True, description="Enable accessibility features")
    color_blind_friendly: bool = Field(default=True, description="Color-blind friendly palettes")
    screen_reader_support: bool = Field(default=True, description="Screen reader support")

    # User context
    user_id: Optional[str] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    user_permissions: List[str] = Field(default_factory=list)

    # Environment context
    base_url: str = Field(default="", description="Base URL for assets")
    cdn_enabled: bool = Field(default=False, description="CDN usage for assets")
    cache_enabled: bool = Field(default=True, description="Enable caching")

    # Debug options
    debug_mode: bool = Field(default=False, description="Enable debug information")
    show_grid: bool = Field(default=False, description="Show layout grid")
    show_component_boundaries: bool = Field(default=False, description="Show component boundaries")


class LayoutEngine:
    """Base layout engine for dashboard generation."""

    def __init__(self, template: DashboardTemplate):
        self.template = template
        self.components: List[ComponentPlacement] = []
        self.optimization_enabled = True

    def add_component(
        self,
        component_type: ComponentType,
        config: Dict[str, Any],
        placement_hints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a component to the layout."""
        component_id = str(uuid.uuid4())

        # Determine optimal placement
        optimal_placement = self._calculate_optimal_placement(
            component_type, config, placement_hints
        )

        # Create component placement
        placement = ComponentPlacement(
            component_id=component_id,
            component_type=component_type,
            **optimal_placement,
            component_config=config
        )

        self.components.append(placement)
        logger.info(f"Added component {component_type.value} with ID {component_id}")

        return component_id

    def optimize_layout(self, context: RenderingContext) -> None:
        """Optimize the layout for the given rendering context."""
        if not self.optimization_enabled:
            return

        logger.info("Optimizing layout for rendering context")

        # Apply responsive optimizations
        self._apply_responsive_optimizations(context)

        # Optimize for performance
        self._apply_performance_optimizations(context)

        # Resolve placement conflicts
        self._resolve_placement_conflicts()

        # Apply accessibility optimizations
        if context.accessibility_enabled:
            self._apply_accessibility_optimizations()

    def get_layout_specification(self) -> Dict[str, Any]:
        """Get the complete layout specification."""
        return {
            "template": self.template.dict(),
            "components": [comp.dict() for comp in self.components],
            "metadata": {
                "total_components": len(self.components),
                "layout_type": self.template.layout_type.value,
                "grid_dimensions": f"{self.template.grid_columns}x{self.template.grid_rows}",
                "responsive_enabled": self.template.responsive_enabled
            }
        }

    def _calculate_optimal_placement(
        self,
        component_type: ComponentType,
        config: Dict[str, Any],
        placement_hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate optimal placement for a component."""
        # Default placement rules based on component type
        placement_rules = {
            ComponentType.HEADER: {"grid_y": 0, "grid_width": self.template.grid_columns, "grid_height": 1},
            ComponentType.METRIC: {"grid_width": 3, "grid_height": 2},
            ComponentType.CHART: {"grid_width": 6, "grid_height": 4},
            ComponentType.TABLE: {"grid_width": 8, "grid_height": 4},
            ComponentType.FILTER: {"grid_width": 4, "grid_height": 1},
            ComponentType.FOOTER: {"grid_y": self.template.grid_rows - 1, "grid_width": self.template.grid_columns, "grid_height": 1}
        }

        # Start with component type defaults
        placement = placement_rules.get(component_type, {"grid_width": 4, "grid_height": 3}).copy()

        # Apply placement hints
        if placement_hints:
            placement.update(placement_hints)

        # Find available position if not specified
        if "grid_x" not in placement or "grid_y" not in placement:
            available_position = self._find_available_position(
                placement.get("grid_width", 4),
                placement.get("grid_height", 3)
            )
            placement.update(available_position)

        return placement

    def _find_available_position(self, width: int, height: int) -> Dict[str, int]:
        """Find available position in the grid."""
        occupied_cells = set()

        # Mark occupied cells
        for comp in self.components:
            for x in range(comp.grid_x, comp.grid_x + comp.grid_width):
                for y in range(comp.grid_y, comp.grid_y + comp.grid_height):
                    occupied_cells.add((x, y))

        # Find available position
        for y in range(self.template.grid_rows - height + 1):
            for x in range(self.template.grid_columns - width + 1):
                # Check if this position can fit the component
                can_fit = True
                for dx in range(width):
                    for dy in range(height):
                        if (x + dx, y + dy) in occupied_cells:
                            can_fit = False
                            break
                    if not can_fit:
                        break

                if can_fit:
                    return {"grid_x": x, "grid_y": y}

        # If no space found, place at end and expand grid if needed
        return {"grid_x": 0, "grid_y": self.template.grid_rows}

    def _apply_responsive_optimizations(self, context: RenderingContext) -> None:
        """Apply responsive design optimizations."""
        if not self.template.responsive_enabled:
            return

        device_type = context.device_type

        # Apply device-specific optimizations
        for component in self.components:
            if device_type in component.responsive_config:
                device_config = component.responsive_config[device_type]

                # Update component placement for this device
                for key, value in device_config.items():
                    if hasattr(component, key):
                        setattr(component, key, value)

    def _apply_performance_optimizations(self, context: RenderingContext) -> None:
        """Apply performance optimizations."""
        if context.lazy_loading:
            # Mark components for lazy loading based on position
            for component in self.components:
                if component.grid_y > 2:  # Components below fold
                    component.component_config["lazy_load"] = True

        if context.data_sampling:
            # Enable data sampling for large datasets
            for component in self.components:
                if component.component_type == ComponentType.CHART:
                    component.component_config["max_data_points"] = context.max_data_points

    def _resolve_placement_conflicts(self) -> None:
        """Resolve any placement conflicts between components."""
        # This is a simplified conflict resolution
        # In a real implementation, this would be much more sophisticated
        pass

    def _apply_accessibility_optimizations(self) -> None:
        """Apply accessibility optimizations."""
        # Ensure proper tab order
        self.components.sort(key=lambda c: (c.grid_y, c.grid_x))

        # Add accessibility attributes
        for i, component in enumerate(self.components):
            component.component_config["tab_index"] = i + 1
            component.component_config["aria_label"] = f"Dashboard component {i + 1}"
