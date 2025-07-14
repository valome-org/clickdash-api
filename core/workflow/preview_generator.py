"""
Preview Generation System.

This module provides dynamic dashboard preview rendering including:
- Interactive preview with sample data
- Multiple layout option presentation
- Performance impact estimation
- Preview validation and optimization
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import json
import logging

from .base import BaseWorkflowStep, WorkflowStep, WorkflowContext
from models.dashboard import DashboardConfig, ChartConfig

logger = logging.getLogger(__name__)


class PreviewType(str, Enum):
    """Types of dashboard previews."""
    STATIC = "static"
    INTERACTIVE = "interactive"
    MOCKUP = "mockup"
    FULL_FEATURED = "full_featured"


class PreviewQuality(str, Enum):
    """Preview quality levels."""
    LOW = "low"           # Fast, basic preview
    MEDIUM = "medium"     # Balanced quality/speed
    HIGH = "high"         # Full quality preview
    ULTRA = "ultra"       # Maximum quality


class LayoutOption(BaseModel):
    """Dashboard layout option."""

    layout_id: str = Field(..., description="Unique layout identifier")
    name: str = Field(..., description="Human-readable layout name")
    description: str = Field(..., description="Layout description")

    # Layout configuration
    grid_columns: int = Field(default=12, description="Grid column count")
    grid_rows: int = Field(default=6, description="Grid row count")
    chart_positions: List[Dict[str, Any]] = Field(default_factory=list)

    # Style configuration
    theme: str = Field(default="default", description="Visual theme")
    color_scheme: str = Field(default="primary", description="Color scheme")
    spacing: str = Field(default="medium", description="Element spacing")

    # Performance characteristics
    estimated_load_time: float = Field(default=0.0, description="Estimated load time in seconds")
    complexity_score: float = Field(default=0.0, description="Layout complexity (0-1)")

    # Preview metadata
    preview_image: Optional[str] = Field(None, description="Preview image URL")
    sample_charts: List[str] = Field(default_factory=list, description="Sample chart types")


class PerformanceImpact(BaseModel):
    """Performance impact assessment."""

    # Loading metrics
    estimated_load_time: float = Field(..., description="Estimated load time in seconds")
    estimated_memory_usage: float = Field(..., description="Estimated memory usage in MB")
    estimated_cpu_usage: float = Field(..., description="Estimated CPU usage percentage")

    # Data metrics
    data_points_count: int = Field(default=0, description="Total data points")
    chart_count: int = Field(default=0, description="Number of charts")
    interactive_elements: int = Field(default=0, description="Interactive elements count")

    # Quality scores
    performance_score: float = Field(..., description="Overall performance score (0-1)")
    optimization_suggestions: List[str] = Field(default_factory=list)

    # User experience impact
    mobile_compatibility: bool = Field(default=True, description="Mobile device compatibility")
    accessibility_score: float = Field(default=1.0, description="Accessibility score (0-1)")


class DashboardPreview(BaseModel):
    """Complete dashboard preview with metadata."""

    preview_id: str = Field(..., description="Unique preview identifier")
    dashboard_config: DashboardConfig = Field(..., description="Dashboard configuration")

    # Preview options
    preview_type: PreviewType = Field(default=PreviewType.INTERACTIVE)
    quality: PreviewQuality = Field(default=PreviewQuality.MEDIUM)

    # Layout alternatives
    layout_options: List[LayoutOption] = Field(default_factory=list)
    recommended_layout: Optional[str] = Field(None, description="Recommended layout ID")

    # Performance assessment
    performance_impact: PerformanceImpact = Field(..., description="Performance impact")

    # Sample data
    sample_data: Dict[str, Any] = Field(default_factory=dict, description="Sample data for preview")
    data_summary: Dict[str, Any] = Field(default_factory=dict, description="Data summary statistics")

    # User guidance
    preview_notes: List[str] = Field(default_factory=list, description="Preview guidance notes")
    implementation_notes: List[str] = Field(default_factory=list, description="Implementation notes")

    # Preview metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Preview expiration")
    generation_time_ms: float = Field(default=0.0)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PreviewRequest(BaseModel):
    """Request for dashboard preview generation."""

    # Core requirements
    dashboard_config: DashboardConfig = Field(..., description="Dashboard to preview")
    data: Dict[str, Any] = Field(..., description="Source data")

    # Preview preferences
    preview_type: PreviewType = Field(default=PreviewType.INTERACTIVE)
    quality: PreviewQuality = Field(default=PreviewQuality.MEDIUM)
    include_alternatives: bool = Field(default=True, description="Include layout alternatives")

    # User context
    user_id: Optional[str] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    device_constraints: Dict[str, Any] = Field(default_factory=dict)

    # Generation options
    max_generation_time: int = Field(default=30, description="Max generation time in seconds")
    max_alternatives: int = Field(default=3, description="Maximum layout alternatives")
    include_performance_analysis: bool = Field(default=True)


class PreviewResult(BaseModel):
    """Result of preview generation."""

    success: bool = Field(..., description="Whether preview generation succeeded")
    preview: Optional[DashboardPreview] = Field(None, description="Generated preview")

    # Generation metadata
    generation_time_ms: float = Field(..., description="Total generation time")
    quality_score: float = Field(..., description="Preview quality score (0-1)")

    # Issues and recommendations
    issues: List[str] = Field(default_factory=list, description="Preview generation issues")
    warnings: List[str] = Field(default_factory=list, description="Preview warnings")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

    # Debug information
    debug_info: Dict[str, Any] = Field(default_factory=dict)


class PreviewGenerator(BaseWorkflowStep):
    """Main preview generation service."""

    def __init__(self):
        super().__init__("preview_generator", WorkflowStep.PREVIEW_GENERATION)
        self.layout_templates = self._load_layout_templates()
        self.performance_calculator = PerformanceCalculator()
        self.sample_data_generator = SampleDataGenerator()

    async def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """Execute preview generation step."""
        try:
            # Extract request data
            request_data = kwargs.get('preview_request')
            if not request_data:
                raise ValueError("Preview request data is required")

            # Create preview request
            if isinstance(request_data, dict):
                preview_request = PreviewRequest(**request_data)
            else:
                preview_request = request_data

            # Generate preview
            result = await self.generate_preview(preview_request)

            # Update workflow context
            if result.success and result.preview:
                context.analysis_context = context.analysis_context or {}
                context.analysis_context['preview'] = result.preview.dict()
                context.current_step = WorkflowStep.USER_REVIEW

            return {
                "step": "preview_generation",
                "success": result.success,
                "preview_id": result.preview.preview_id if result.preview else None,
                "generation_time_ms": result.generation_time_ms,
                "quality_score": result.quality_score
            }

        except Exception as e:
            logger.error(f"Preview generation failed: {str(e)}")
            raise

    async def validate_inputs(self, context: WorkflowContext, **kwargs) -> bool:
        """Validate inputs for preview generation."""
        request_data = kwargs.get('preview_request')
        if not request_data:
            return False

        # Validate dashboard config exists
        if isinstance(request_data, dict):
            return 'dashboard_config' in request_data and 'data' in request_data

        return hasattr(request_data, 'dashboard_config') and hasattr(request_data, 'data')

    async def generate_preview(self, request: PreviewRequest) -> PreviewResult:
        """
        Generate comprehensive dashboard preview.

        Args:
            request: Preview generation request

        Returns:
            PreviewResult with generated preview
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Generating {request.preview_type.value} preview with {request.quality.value} quality")

            # Generate sample data
            sample_data = await self.sample_data_generator.generate_sample_data(
                request.data, request.dashboard_config
            )

            # Calculate performance impact
            performance_impact = await self.performance_calculator.calculate_impact(
                request.dashboard_config, request.data
            )

            # Generate layout alternatives
            layout_options = []
            if request.include_alternatives:
                layout_options = await self._generate_layout_alternatives(
                    request.dashboard_config, request.max_alternatives
                )

            # Select recommended layout
            recommended_layout = await self._select_recommended_layout(
                layout_options, request.user_preferences
            )

            # Generate preview notes
            preview_notes = await self._generate_preview_notes(
                request.dashboard_config, performance_impact
            )
            implementation_notes = await self._generate_implementation_notes(
                request.dashboard_config, request.device_constraints
            )

            # Calculate generation time
            end_time = datetime.utcnow()
            generation_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create preview
            preview = DashboardPreview(
                preview_id=f"preview_{int(datetime.utcnow().timestamp())}",
                dashboard_config=request.dashboard_config,
                preview_type=request.preview_type,
                quality=request.quality,
                layout_options=layout_options,
                recommended_layout=recommended_layout,
                performance_impact=performance_impact,
                sample_data=sample_data,
                data_summary=await self._generate_data_summary(request.data),
                preview_notes=preview_notes,
                implementation_notes=implementation_notes,
                generation_time_ms=generation_time_ms,
                expires_at=None
            )

            # Calculate quality score
            quality_score = await self._calculate_preview_quality(preview)

            logger.info(f"Preview generated successfully: {preview.preview_id}")

            return PreviewResult(
                success=True,
                preview=preview,
                generation_time_ms=generation_time_ms,
                quality_score=quality_score,
                recommendations=await self._generate_recommendations(preview)
            )

        except Exception as e:
            end_time = datetime.utcnow()
            generation_time_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(f"Preview generation failed: {str(e)}")

            return PreviewResult(
                success=False,
                preview=None,
                generation_time_ms=generation_time_ms,
                quality_score=0.0,
                issues=[str(e)],
                debug_info={"error": str(e), "timestamp": end_time.isoformat()}
            )

    async def _generate_layout_alternatives(
        self,
        dashboard_config: DashboardConfig,
        max_alternatives: int
    ) -> List[LayoutOption]:
        """Generate alternative layout options."""
        alternatives = []

        # Template-based layouts
        for template_id, template in list(self.layout_templates.items())[:max_alternatives]:
            layout = LayoutOption(
                layout_id=template_id,
                name=template["name"],
                description=template["description"],
                grid_columns=template.get("grid_columns", 12),
                grid_rows=template.get("grid_rows", 6),
                chart_positions=await self._adapt_chart_positions(
                    dashboard_config.charts, template
                ),
                theme=template.get("theme", "default"),
                color_scheme=template.get("color_scheme", "primary"),
                estimated_load_time=template.get("estimated_load_time", 2.0),
                complexity_score=template.get("complexity_score", 0.5),
                preview_image=None
            )
            alternatives.append(layout)

        return alternatives

    async def _adapt_chart_positions(
        self,
        charts: List[ChartConfig],
        template: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Adapt chart positions to layout template."""
        positions = []
        grid_positions = template.get("positions", [])

        for i, chart in enumerate(charts):
            if i < len(grid_positions):
                position = grid_positions[i].copy()
                position["chart_id"] = f"chart_{i}"
                position["chart_type"] = chart.chart_type
                positions.append(position)

        return positions

    async def _select_recommended_layout(
        self,
        layout_options: List[LayoutOption],
        user_preferences: Dict[str, Any]
    ) -> Optional[str]:
        """Select the recommended layout based on preferences."""
        if not layout_options:
            return None

        # Score layouts based on user preferences
        scored_layouts = []
        for layout in layout_options:
            score = 0.0

            # Performance preference
            if user_preferences.get("prefer_fast_loading", False):
                score += (1.0 - layout.complexity_score) * 0.3

            # Simplicity preference
            if user_preferences.get("prefer_simple_layout", False):
                score += (1.0 - layout.complexity_score) * 0.4

            # Visual preference
            preferred_theme = user_preferences.get("preferred_theme")
            if preferred_theme and layout.theme == preferred_theme:
                score += 0.3

            scored_layouts.append((layout.layout_id, score))

        # Return highest scoring layout
        scored_layouts.sort(key=lambda x: x[1], reverse=True)
        return scored_layouts[0][0]

    async def _generate_preview_notes(
        self,
        dashboard_config: DashboardConfig,
        performance_impact: PerformanceImpact
    ) -> List[str]:
        """Generate helpful preview notes for users."""
        notes = []

        # Performance notes
        if performance_impact.estimated_load_time > 5:
            notes.append("This dashboard may take longer to load due to data complexity")

        if performance_impact.chart_count > 10:
            notes.append("Consider reducing the number of charts for better performance")

        # Chart-specific notes
        chart_types = [chart.chart_type for chart in dashboard_config.charts]
        if "scatter" in chart_types and performance_impact.data_points_count > 1000:
            notes.append("Scatter plots with large datasets may benefit from data sampling")

        # Mobile compatibility
        if not performance_impact.mobile_compatibility:
            notes.append("This layout may not display optimally on mobile devices")

        return notes

    async def _generate_implementation_notes(
        self,
        dashboard_config: DashboardConfig,
        device_constraints: Dict[str, Any]
    ) -> List[str]:
        """Generate implementation-specific notes."""
        notes = []

        # Device-specific notes
        if device_constraints.get("mobile_device", False):
            notes.append("Charts will be optimized for mobile viewing")

        if device_constraints.get("low_bandwidth", False):
            notes.append("Data loading will be optimized for low bandwidth connections")

        # Feature notes
        interactive_charts = [c for c in dashboard_config.charts if hasattr(c, 'interactive_features')]
        if interactive_charts:
            notes.append("Interactive features will be enabled for supported charts")

        return notes

    async def _generate_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for the data."""
        return {
            "total_fields": len(data.keys()) if isinstance(data, dict) else 0,
            "estimated_rows": 100,  # This would be calculated from actual data
            "data_types": "mixed",
            "last_updated": datetime.utcnow().isoformat()
        }

    async def _calculate_preview_quality(self, preview: DashboardPreview) -> float:
        """Calculate overall preview quality score."""
        quality_factors = []

        # Performance quality
        quality_factors.append(preview.performance_impact.performance_score)

        # Layout quality
        if preview.layout_options:
            avg_complexity = sum(lo.complexity_score for lo in preview.layout_options) / len(preview.layout_options)
            quality_factors.append(1.0 - avg_complexity)  # Lower complexity = higher quality

        # Generation time quality
        if preview.generation_time_ms < 5000:  # Under 5 seconds
            quality_factors.append(1.0)
        elif preview.generation_time_ms < 15000:  # Under 15 seconds
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.4)

        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5

    async def _generate_recommendations(self, preview: DashboardPreview) -> List[str]:
        """Generate improvement recommendations for the preview."""
        recommendations = []

        # Performance recommendations
        if preview.performance_impact.estimated_load_time > 3:
            recommendations.append("Consider reducing data complexity to improve load times")

        if preview.performance_impact.chart_count > 8:
            recommendations.append("Consider grouping related charts or using tabs")

        # Layout recommendations
        if preview.recommended_layout:
            recommendations.append(f"We recommend the '{preview.recommended_layout}' layout for optimal user experience")

        return recommendations

    def _load_layout_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined layout templates."""
        return {
            "dashboard_classic": {
                "name": "Classic Dashboard",
                "description": "Traditional dashboard layout with header metrics and chart grid",
                "grid_columns": 12,
                "grid_rows": 8,
                "theme": "professional",
                "complexity_score": 0.4,
                "estimated_load_time": 2.0,
                "positions": [
                    {"x": 0, "y": 0, "w": 3, "h": 2},  # Top left metric
                    {"x": 3, "y": 0, "w": 3, "h": 2},  # Top center metric
                    {"x": 6, "y": 0, "w": 6, "h": 2},  # Top right chart
                    {"x": 0, "y": 2, "w": 8, "h": 4},  # Main chart
                    {"x": 8, "y": 2, "w": 4, "h": 4},  # Side chart
                ]
            },
            "executive_summary": {
                "name": "Executive Summary",
                "description": "Clean, high-level overview suitable for executives",
                "grid_columns": 12,
                "grid_rows": 6,
                "theme": "minimal",
                "complexity_score": 0.2,
                "estimated_load_time": 1.5,
                "positions": [
                    {"x": 0, "y": 0, "w": 12, "h": 2},  # Header metrics
                    {"x": 0, "y": 2, "w": 6, "h": 4},   # Main chart
                    {"x": 6, "y": 2, "w": 6, "h": 4},   # Secondary chart
                ]
            },
            "analytical_deep_dive": {
                "name": "Analytical Deep Dive",
                "description": "Detailed layout for comprehensive data analysis",
                "grid_columns": 12,
                "grid_rows": 10,
                "theme": "analytical",
                "complexity_score": 0.8,
                "estimated_load_time": 4.0,
                "positions": [
                    {"x": 0, "y": 0, "w": 4, "h": 3},   # Chart 1
                    {"x": 4, "y": 0, "w": 4, "h": 3},   # Chart 2
                    {"x": 8, "y": 0, "w": 4, "h": 3},   # Chart 3
                    {"x": 0, "y": 3, "w": 6, "h": 4},   # Main analysis
                    {"x": 6, "y": 3, "w": 6, "h": 4},   # Supporting analysis
                    {"x": 0, "y": 7, "w": 12, "h": 3},  # Summary table
                ]
            }
        }


class PerformanceCalculator:
    """Calculates performance impact of dashboard configurations."""

    async def calculate_impact(
        self,
        dashboard_config: DashboardConfig,
        data: Dict[str, Any]
    ) -> PerformanceImpact:
        """Calculate performance impact for dashboard configuration."""

        # Estimate data characteristics
        data_points = await self._estimate_data_points(data)
        chart_count = len(dashboard_config.charts)
        interactive_elements = await self._count_interactive_elements(dashboard_config)

        # Calculate load time
        base_load_time = 1.0  # Base 1 second
        data_load_time = min(data_points / 1000, 5.0)  # Max 5 seconds for data
        chart_load_time = chart_count * 0.5  # 0.5 seconds per chart
        interaction_load_time = interactive_elements * 0.2  # 0.2 seconds per interaction

        estimated_load_time = base_load_time + data_load_time + chart_load_time + interaction_load_time

        # Calculate memory usage (simplified)
        estimated_memory = (data_points * 0.001) + (chart_count * 2) + 10  # MB

        # Calculate CPU usage (simplified)
        estimated_cpu = min((chart_count * 5) + (interactive_elements * 10), 100)  # Percentage

        # Calculate performance score
        performance_score = max(0.0, 1.0 - (estimated_load_time / 10.0))

        # Generate optimization suggestions
        suggestions = []
        if estimated_load_time > 5:
            suggestions.append("Consider data pagination or sampling")
        if chart_count > 10:
            suggestions.append("Consider chart grouping or lazy loading")
        if interactive_elements > 20:
            suggestions.append("Reduce interactive elements for better performance")

        # Check mobile compatibility
        mobile_compatible = chart_count <= 6 and estimated_load_time <= 8

        return PerformanceImpact(
            estimated_load_time=estimated_load_time,
            estimated_memory_usage=estimated_memory,
            estimated_cpu_usage=estimated_cpu,
            data_points_count=data_points,
            chart_count=chart_count,
            interactive_elements=interactive_elements,
            performance_score=performance_score,
            optimization_suggestions=suggestions,
            mobile_compatibility=mobile_compatible,
            accessibility_score=0.9  # Default high accessibility
        )

    async def _estimate_data_points(self, data: Dict[str, Any]) -> int:
        """Estimate total data points in the dataset."""
        if isinstance(data, dict):
            # Simple estimation based on structure
            return len(data) * 10  # Rough estimate
        return 100  # Default

    async def _count_interactive_elements(self, dashboard_config: DashboardConfig) -> int:
        """Count interactive elements in dashboard."""
        count = 0
        for chart in dashboard_config.charts:
            # Count based on chart type and features
            if hasattr(chart, 'interactive_features') and chart.interactive_features:
                count += len(chart.interactive_features)
            else:
                # Default interactive elements per chart type
                if chart.chart_type in ['scatter', 'line', 'area']:
                    count += 3  # Zoom, pan, tooltip
                elif chart.chart_type in ['bar', 'column']:
                    count += 2  # Click, tooltip
                else:
                    count += 1  # Basic interaction

        return count


class SampleDataGenerator:
    """Generates sample data for dashboard previews."""

    async def generate_sample_data(
        self,
        original_data: Dict[str, Any],
        dashboard_config: DashboardConfig
    ) -> Dict[str, Any]:
        """Generate sample data suitable for previews."""

        # For now, return a simplified version of the original data
        # In a full implementation, this would intelligently sample
        # and anonymize the data while preserving characteristics

        sample_data = {}

        if isinstance(original_data, dict):
            # Take a sample of the original data
            for key, value in list(original_data.items())[:10]:  # First 10 items
                if isinstance(value, list):
                    sample_data[key] = value[:5]  # First 5 list items
                else:
                    sample_data[key] = value

        return sample_data
