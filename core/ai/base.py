"""
Base interfaces and types for AI analysis system.

This module defines the fundamental interfaces and data types used
throughout the AI analysis and recommendation system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    GOOGLE_GEMINI = "google_gemini"
    AZURE_OPENAI = "azure_openai"
    OLLAMA_LOCAL = "ollama_local"


class RecommendationType(str, Enum):
    """Types of AI recommendations."""
    CHART_TYPE = "chart_type"
    LAYOUT_DESIGN = "layout_design"
    COLOR_SCHEME = "color_scheme"
    DATA_AGGREGATION = "data_aggregation"
    FILTERING = "filtering"
    GROUPING = "grouping"
    METRIC_CALCULATION = "metric_calculation"
    INSIGHT_GENERATION = "insight_generation"
    VISUALIZATION_ENHANCEMENT = "visualization_enhancement"
    DASHBOARD_STRUCTURE = "dashboard_structure"


class ConfidenceLevel(str, Enum):
    """Confidence levels for AI analysis results."""
    VERY_LOW = "very_low"    # 0.0 - 0.2
    LOW = "low"              # 0.2 - 0.4
    MEDIUM = "medium"        # 0.4 - 0.6
    HIGH = "high"            # 0.6 - 0.8
    VERY_HIGH = "very_high"  # 0.8 - 1.0


class AnalysisContext(BaseModel):
    """Context information for AI analysis."""

    # Data context
    dataset_id: Optional[str] = None
    column_count: int = 0
    row_count: int = 0
    data_types: Dict[str, str] = Field(default_factory=dict)

    # Business context
    business_domain: Optional[str] = None
    use_case: Optional[str] = None
    target_audience: Optional[str] = None

    # User context
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    previous_choices: List[Dict[str, Any]] = Field(default_factory=list)

    # Technical context
    platform_constraints: Dict[str, Any] = Field(default_factory=dict)
    performance_requirements: Dict[str, Any] = Field(default_factory=dict)

    # Metadata context
    metadata_quality: float = 0.0
    completeness_score: float = 0.0

    # Analysis constraints
    max_processing_time: int = Field(default=30, description="Max processing time in seconds")
    required_confidence: float = Field(default=0.6, description="Minimum confidence threshold")


class AnalysisResult(BaseModel):
    """Result of AI analysis operation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recommendation_type: RecommendationType = Field(..., description="Type of recommendation")

    # Core recommendation
    primary_recommendation: Dict[str, Any] = Field(..., description="Main recommendation")
    alternative_options: List[Dict[str, Any]] = Field(default_factory=list)

    # Confidence and validation
    confidence_score: float = Field(..., description="Overall confidence (0.0-1.0)")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence classification")

    # Reasoning and explanation
    reasoning: str = Field(..., description="AI reasoning for the recommendation")
    explanation: str = Field(..., description="Human-readable explanation")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made")

    # Supporting evidence
    supporting_data: Dict[str, Any] = Field(default_factory=dict)
    metadata_factors: List[str] = Field(default_factory=list)

    # Analysis metadata
    llm_provider: LLMProvider = Field(..., description="Primary LLM used")
    consensus_providers: List[LLMProvider] = Field(default_factory=list)
    analysis_time_ms: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Validation results
    validation_passed: bool = Field(default=True)
    validation_issues: List[str] = Field(default_factory=list)

    @classmethod
    def determine_confidence_level(cls, score: float) -> ConfidenceLevel:
        """Determine confidence level from numerical score."""
        if score >= 0.8:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.6:
            return ConfidenceLevel.HIGH
        elif score >= 0.4:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.2:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


class AIAnalysisInterface(ABC):
    """
    Base interface for all AI analysis components.
    """

    def __init__(self, context: Optional[AnalysisContext] = None):
        self.context = context or AnalysisContext()

    @abstractmethod
    async def analyze(self, data: Any, **kwargs) -> AnalysisResult:
        """Perform AI analysis on the provided data."""
        pass

    @abstractmethod
    async def validate_result(self, result: AnalysisResult) -> bool:
        """Validate the analysis result for quality and consistency."""
        pass

    def update_context(self, **kwargs):
        """Update analysis context with new information."""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

    def get_confidence_threshold(self) -> float:
        """Get the minimum confidence threshold for results."""
        return self.context.required_confidence
