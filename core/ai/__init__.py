"""
AI Analysis and Recommendation Engine.

This module provides AI-powered analysis and recommendation capabilities including:
- Multi-LLM analysis pipeline
- Context-aware prompt engineering
- Recommendation validation system
- Confidence scoring and consensus building
"""

from .base import (
    AIAnalysisInterface,
    LLMProvider,
    AnalysisContext,
    AnalysisResult,
    RecommendationType,
    ConfidenceLevel
)

from .analysis_pipeline import (
    MultiLLMAnalyzer,
    LLMAnalysisResult,
    ConsensusBuilder,
    AnalysisRequest
)

from .prompt_engineering import (
    PromptTemplate,
    ContextAwarePromptBuilder,
    PromptValidationResult,
    IndustryPromptLibrary
)

from .validation_system import (
    RecommendationValidator,
    ValidationRule,
    ValidationResult,
    LogicalConsistencyChecker
)

from .ai_service import (
    AIAnalysisService,
    RecommendationRequest,
    RecommendationResponse
)

__all__ = [
    # Base interfaces
    "AIAnalysisInterface",
    "LLMProvider",
    "AnalysisContext",
    "AnalysisResult",
    "RecommendationType",
    "ConfidenceLevel",

    # Analysis pipeline
    "MultiLLMAnalyzer",
    "LLMAnalysisResult",
    "ConsensusBuilder",
    "AnalysisRequest",

    # Prompt engineering
    "PromptTemplate",
    "ContextAwarePromptBuilder",
    "PromptValidationResult",
    "IndustryPromptLibrary",

    # Validation system
    "RecommendationValidator",
    "ValidationRule",
    "ValidationResult",
    "LogicalConsistencyChecker",

    # Main service
    "AIAnalysisService",
    "RecommendationRequest",
    "RecommendationResponse"
]
