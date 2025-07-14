"""
Dynamic Dashboard Builder.

This module provides comprehensive dashboard generation including:
- Template-based dashboard generation
- Custom layout engine with intelligent component placement
- Interactive component rendering
- Responsive design implementation
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import json
import logging
import uuid

from .base import (
    DashboardTemplate, LayoutEngine, ComponentPlacement, RenderingContext,
    ComponentType, LayoutType, ResponsiveBreakpoint
)
from models.dashboard import DashboardConfig, ChartConfig

logger = logging.getLogger(__name__)


class GenerationStrategy(str, Enum):
    """Dashboard generation strategies."""
    TEMPLATE_BASED = "template_based"
    AI_OPTIMIZED = "ai_optimized"
    USER_GUIDED = "user_guided"
    PERFORMANCE_FIRST = "performance_first"
    MOBILE_FIRST = "mobile_first"


class ComponentRenderer:
    """Renders individual dashboard components."""

    def __init__(self):
        self.supported_formats = ["html", "react", "vue", "json"]
        self.component_templates = self._load_component_templates()

    async def render_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Render a single component."""
        try:
            component_type = placement.component_type
            config = placement.component_config

            logger.info(f"Rendering component {component_type.value} with ID {placement.component_id}")

            # Get component template
            template = self.component_templates.get(component_type, {})

            # Render based on component type
            if component_type == ComponentType.CHART:
                return await self._render_chart_component(placement, context, data, template)
            elif component_type == ComponentType.METRIC:
                return await self._render_metric_component(placement, context, data, template)
            elif component_type == ComponentType.TABLE:
                return await self._render_table_component(placement, context, data, template)
            elif component_type == ComponentType.HEADER:
                return await self._render_header_component(placement, context, template)
            elif component_type == ComponentType.FILTER:
                return await self._render_filter_component(placement, context, data, template)
            else:
                return await self._render_generic_component(placement, context, template)

        except Exception as e:
            logger.error(f"Failed to render component {placement.component_id}: {str(e)}")
            return self._render_error_component(placement, str(e))

    async def _render_chart_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        data: Optional[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render a chart component."""
        config = placement.component_config
        chart_type = config.get("chart_type", "bar")

        # Generate chart configuration
        chart_config = {
            "type": chart_type,
            "data": data or config.get("data", {}),
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": config.get("title", "Chart")
                    },
                    "legend": {
                        "display": config.get("show_legend", True),
                        "position": config.get("legend_position", "top")
                    }
                },
                "scales": self._generate_chart_scales(chart_type, config),
                "interaction": {
                    "intersect": False,
                    "mode": "index"
                } if context.interactive else {}
            }
        }

        # Apply responsive configurations
        if context.device_type == ResponsiveBreakpoint.MOBILE:
            chart_config["options"]["plugins"]["legend"]["position"] = "bottom"
            chart_config["options"]["plugins"]["title"]["font"] = {"size": 14}

        return {
            "component_type": "chart",
            "component_id": placement.component_id,
            "config": chart_config,
            "positioning": self._generate_positioning(placement),
            "styling": self._generate_component_styling(placement, context),
            "interactivity": self._generate_interactivity_config(config, context)
        }

    async def _render_metric_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        data: Optional[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render a metric component."""
        config = placement.component_config

        return {
            "component_type": "metric",
            "component_id": placement.component_id,
            "config": {
                "title": config.get("title", "Metric"),
                "value": config.get("value", "N/A"),
                "format": config.get("format", "number"),
                "trend": config.get("trend", None),
                "comparison": config.get("comparison", None),
                "icon": config.get("icon", None),
                "color_scheme": config.get("color_scheme", "primary")
            },
            "positioning": self._generate_positioning(placement),
            "styling": self._generate_component_styling(placement, context),
            "animations": self._generate_animation_config(config, context)
        }

    async def _render_table_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        data: Optional[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render a table component."""
        config = placement.component_config

        return {
            "component_type": "table",
            "component_id": placement.component_id,
            "config": {
                "title": config.get("title", "Data Table"),
                "columns": config.get("columns", []),
                "data": data or config.get("data", []),
                "pagination": config.get("pagination", {"enabled": True, "page_size": 10}),
                "sorting": config.get("sorting", {"enabled": True}),
                "filtering": config.get("filtering", {"enabled": False}),
                "export": config.get("export", {"enabled": True, "formats": ["csv", "excel"]})
            },
            "positioning": self._generate_positioning(placement),
            "styling": self._generate_component_styling(placement, context),
            "responsive": self._generate_table_responsive_config(context)
        }

    async def _render_header_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render a header component."""
        config = placement.component_config

        return {
            "component_type": "header",
            "component_id": placement.component_id,
            "config": {
                "title": config.get("title", "Dashboard"),
                "subtitle": config.get("subtitle", ""),
                "logo": config.get("logo", None),
                "actions": config.get("actions", []),
                "breadcrumbs": config.get("breadcrumbs", [])
            },
            "positioning": self._generate_positioning(placement),
            "styling": self._generate_header_styling(placement, context)
        }

    async def _render_filter_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        data: Optional[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render a filter component."""
        config = placement.component_config

        return {
            "component_type": "filter",
            "component_id": placement.component_id,
            "config": {
                "filters": config.get("filters", []),
                "layout": config.get("layout", "horizontal"),
                "apply_mode": config.get("apply_mode", "auto"),
                "reset_enabled": config.get("reset_enabled", True)
            },
            "positioning": self._generate_positioning(placement),
            "styling": self._generate_component_styling(placement, context),
            "interactivity": self._generate_filter_interactivity(config, context)
        }

    async def _render_generic_component(
        self,
        placement: ComponentPlacement,
        context: RenderingContext,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render a generic component."""
        config = placement.component_config

        return {
            "component_type": placement.component_type.value,
            "component_id": placement.component_id,
            "config": config,
            "positioning": self._generate_positioning(placement),
            "styling": self._generate_component_styling(placement, context)
        }

    def _render_error_component(self, placement: ComponentPlacement, error: str) -> Dict[str, Any]:
        """Render an error component when rendering fails."""
        return {
            "component_type": "error",
            "component_id": placement.component_id,
            "config": {
                "title": "Component Error",
                "message": error,
                "type": placement.component_type.value
            },
            "positioning": self._generate_positioning(placement),
            "styling": {"background": "#fee", "border": "1px solid #fcc", "padding": "16px"}
        }

    def _generate_positioning(self, placement: ComponentPlacement) -> Dict[str, Any]:
        """Generate positioning configuration for a component."""
        return {
            "grid": {
                "column": placement.grid_x + 1,  # CSS Grid is 1-indexed
                "row": placement.grid_y + 1,
                "column_span": placement.grid_width,
                "row_span": placement.grid_height
            },
            "absolute": {
                "x": placement.absolute_x,
                "y": placement.absolute_y,
                "width": placement.absolute_width,
                "height": placement.absolute_height
            } if placement.absolute_x is not None else None,
            "constraints": {
                "min_width": placement.min_width,
                "min_height": placement.min_height,
                "max_width": placement.max_width,
                "max_height": placement.max_height
            },
            "z_index": placement.z_index
        }

    def _generate_component_styling(
        self,
        placement: ComponentPlacement,
        context: RenderingContext
    ) -> Dict[str, Any]:
        """Generate styling configuration for a component."""
        base_styling = {
            "margin": placement.margin,
            "padding": placement.padding,
            "border_radius": "8px",
            "box_shadow": "0 2px 4px rgba(0,0,0,0.1)" if not context.print_friendly else "none",
            "background": "#ffffff"
        }

        # Apply style overrides
        base_styling.update(placement.style_overrides)

        # Apply context-specific styling
        if context.print_friendly:
            base_styling.update({
                "background": "#ffffff",
                "color": "#000000",
                "box_shadow": "none"
            })

        if context.high_dpi:
            base_styling["font_size"] = "14px"

        return base_styling

    def _generate_chart_scales(self, chart_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart scales configuration."""
        scales = {}

        if chart_type in ["bar", "line", "area"]:
            scales["x"] = {
                "display": True,
                "title": {
                    "display": True,
                    "text": config.get("x_axis_label", "X Axis")
                }
            }
            scales["y"] = {
                "display": True,
                "title": {
                    "display": True,
                    "text": config.get("y_axis_label", "Y Axis")
                }
            }

        return scales

    def _load_component_templates(self) -> Dict[ComponentType, Dict[str, Any]]:
        """Load component templates."""
        return {
            ComponentType.CHART: {"default_config": {"responsive": True}},
            ComponentType.METRIC: {"default_config": {"format": "number"}},
            ComponentType.TABLE: {"default_config": {"pagination": True}},
            ComponentType.HEADER: {"default_config": {"show_logo": True}},
            ComponentType.FILTER: {"default_config": {"apply_mode": "auto"}}
        }

    def _generate_interactivity_config(self, config: Dict[str, Any], context: RenderingContext) -> Dict[str, Any]:
        """Generate interactivity configuration."""
        if not context.interactive:
            return {"enabled": False}

        return {
            "enabled": True,
            "hover_effects": config.get("hover_effects", True),
            "click_actions": config.get("click_actions", []),
            "tooltips": config.get("tooltips", {"enabled": True})
        }

    def _generate_animation_config(self, config: Dict[str, Any], context: RenderingContext) -> Dict[str, Any]:
        """Generate animation configuration."""
        if context.print_friendly:
            return {"enabled": False}

        return {
            "enabled": config.get("animations", True),
            "duration": config.get("animation_duration", 300),
            "easing": config.get("animation_easing", "ease-in-out")
        }

    def _generate_table_responsive_config(self, context: RenderingContext) -> Dict[str, Any]:
        """Generate table responsive configuration."""
        if context.device_type == ResponsiveBreakpoint.MOBILE:
            return {
                "scroll_horizontal": True,
                "column_priority": ["1", "2", "3"],
                "collapse_columns": True
            }

        return {
            "scroll_horizontal": False,
            "column_priority": [],
            "collapse_columns": False
        }

    def _generate_header_styling(self, placement: ComponentPlacement, context: RenderingContext) -> Dict[str, Any]:
        """Generate header-specific styling."""
        base_styling = self._generate_component_styling(placement, context)

        header_styling = {
            "background": "#f8f9fa",
            "border_bottom": "1px solid #dee2e6",
            "padding": "16px 24px",
            "font_weight": "600"
        }

        base_styling.update(header_styling)
        return base_styling

    def _generate_filter_interactivity(self, config: Dict[str, Any], context: RenderingContext) -> Dict[str, Any]:
        """Generate filter interactivity configuration."""
        if not context.interactive:
            return {"enabled": False}

        return {
            "enabled": True,
            "auto_apply": config.get("apply_mode", "auto") == "auto",
            "debounce_delay": config.get("debounce_delay", 300),
            "clear_all": config.get("reset_enabled", True)
        }


class DashboardGenerationRequest(BaseModel):
    """Request for dashboard generation."""

    dashboard_config: Any = Field(..., description="Dashboard configuration")
    data: Dict[str, Any] = Field(default_factory=dict, description="Source data")
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy: GenerationStrategy = Field(default=GenerationStrategy.AI_OPTIMIZED)


class DashboardGenerationResult(BaseModel):
    """Result of dashboard generation."""

    success: bool = Field(..., description="Whether generation succeeded")
    dashboard_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generation_id: str = Field(..., description="Generation identifier")
    generation_strategy: GenerationStrategy = Field(default=GenerationStrategy.AI_OPTIMIZED)
    rendered_components: List[Dict[str, Any]] = Field(default_factory=list)
    layout_config: Dict[str, Any] = Field(default_factory=dict)
    layout_specification: Dict[str, Any] = Field(default_factory=dict)

    # Quality scores
    performance_score: Optional[float] = Field(default=None)
    accessibility_score: Optional[float] = Field(default=None)
    responsive_score: Optional[float] = Field(default=None)

    # Feedback
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Timing
    generation_time_ms: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DashboardBuilder:
    """Main dashboard generation service."""

    def __init__(self):
        self.component_renderer = ComponentRenderer()
        self.layout_engine = None  # Initialize as needed

    async def generate_dashboard(self, request: DashboardGenerationRequest) -> DashboardGenerationResult:
        """Generate a complete dashboard from the request."""
        try:
            start_time = datetime.utcnow()

            logger.info(f"Generating dashboard with strategy: {request.strategy}")

            # Create basic result
            result = DashboardGenerationResult(
                success=True,
                generation_id=request.generation_id,
                generation_strategy=request.strategy
            )

            # Basic dashboard layout
            result.layout_config = {
                "type": "grid",
                "columns": 12,
                "rows": "auto",
                "gap": "16px"
            }

            # Generate basic components based on data
            if request.data:
                components = await self._generate_components_from_data(request.data)
                result.rendered_components = components

            # Calculate generation time
            end_time = datetime.utcnow()
            result.generation_time_ms = (end_time - start_time).total_seconds() * 1000

            return result

        except Exception as e:
            logger.error(f"Dashboard generation failed: {str(e)}")
            return DashboardGenerationResult(
                success=False,
                generation_id=request.generation_id,
                errors=[str(e)]
            )

    async def _generate_components_from_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate components based on available data."""
        components = []

        # Add header component
        components.append({
            "component_type": "header",
            "component_id": str(uuid.uuid4()),
            "config": {
                "title": "Generated Dashboard",
                "subtitle": f"Based on {len(data)} data sources"
            }
        })

        return components
