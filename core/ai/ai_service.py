"""
AI Analysis Service.

This module provides the main AI analysis service that coordinates:
- Multi-LLM analysis pipeline
- Context-aware prompt engineering
- Recommendation validation
- Result optimization and delivery
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import asyncio

from .base import (
    AnalysisContext,
    AnalysisResult,
    RecommendationType,
    LLMProvider
)
from .analysis_pipeline import MultiLLMAnalyzer, AnalysisRequest
from .prompt_engineering import ContextAwarePromptBuilder, IndustryPromptLibrary
from .validation_system import RecommendationValidator, ValidationResult

logger = logging.getLogger(__name__)


class RecommendationRequest(BaseModel):
    """Request for AI analysis and recommendations."""

    # Data and context
    data: Dict[str, Any] = Field(..., description="Data to analyze")
    recommendation_type: RecommendationType = Field(..., description="Type of recommendation needed")
    context: AnalysisContext = Field(default_factory=AnalysisContext)

    # Analysis preferences
    preferred_provider: LLMProvider = Field(default=LLMProvider.OPENAI_GPT4)
    enable_multi_llm: bool = Field(default=True, description="Use multiple LLMs for consensus")
    enable_validation: bool = Field(default=True, description="Validate recommendations")

    # Quality requirements
    min_confidence: float = Field(default=0.6, description="Minimum confidence threshold")
    max_processing_time: int = Field(default=30, description="Maximum processing time in seconds")

    # User preferences
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))


class RecommendationResponse(BaseModel):
    """Response from AI analysis service."""

    # Request tracking
    request_id: str = Field(..., description="Original request ID")
    success: bool = Field(..., description="Whether analysis succeeded")

    # Core results
    recommendation: Optional[AnalysisResult] = Field(None, description="Primary recommendation")
    alternatives: List[AnalysisResult] = Field(default_factory=list, description="Alternative recommendations")

    # Validation results
    validation: Optional[ValidationResult] = Field(None, description="Validation results")

    # Processing metadata
    processing_time_ms: float = Field(..., description="Total processing time")
    llm_providers_used: List[LLMProvider] = Field(default_factory=list)
    consensus_achieved: bool = Field(default=False)

    # Quality indicators
    overall_confidence: float = Field(..., description="Overall confidence score")
    quality_score: float = Field(..., description="Overall quality score")

    # User guidance
    explanation: str = Field(..., description="Human-readable explanation")
    next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")
    warnings: List[str] = Field(default_factory=list, description="Important warnings")

    # Debugging information
    debug_info: Dict[str, Any] = Field(default_factory=dict, description="Debug information")

    # Response metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")


class AIAnalysisService:
    """Main AI analysis service coordinating all AI components."""

    def __init__(self, context: Optional[AnalysisContext] = None):
        self.default_context = context or AnalysisContext()

        # Initialize components
        self.llm_analyzer = MultiLLMAnalyzer(self.default_context)
        self.prompt_builder = ContextAwarePromptBuilder()
        self.validator = RecommendationValidator()
        self.industry_library = IndustryPromptLibrary()

        # Service configuration
        self.max_concurrent_requests = 10
        self.default_timeout = 30
        self.enable_caching = True
        self.cache = {}  # Simple in-memory cache

        logger.info("AI Analysis Service initialized")

    async def analyze_and_recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Perform comprehensive AI analysis and generate recommendations.

        Args:
            request: Analysis request with data and preferences

        Returns:
            RecommendationResponse with recommendations and validation
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting AI analysis for request {request.request_id}")

            # Merge contexts
            analysis_context = await self._merge_contexts(request.context, request)

            # Check cache if enabled
            if self.enable_caching:
                cached_result = await self._check_cache(request)
                if cached_result:
                    logger.info(f"Returning cached result for request {request.request_id}")
                    return cached_result

            # Build context-aware prompt
            prompt = await self.prompt_builder.build_prompt(
                recommendation_type=request.recommendation_type,
                context=analysis_context,
                data=request.data,
                user_preferences=analysis_context.user_preferences
            )

            # Run AI analysis
            if request.enable_multi_llm:
                analysis_result = await self._run_multi_llm_analysis(request, analysis_context, prompt)
            else:
                analysis_result = await self._run_single_llm_analysis(request, analysis_context, prompt)

            # Validate recommendations if enabled
            validation_result = None
            if request.enable_validation:
                validation_result = await self.validator.validate_recommendation(
                    analysis_result, analysis_context
                )

                # Apply fixes if validation failed
                if not validation_result.is_valid:
                    analysis_result = await self._apply_validation_fixes(
                        analysis_result, validation_result, analysis_context
                    )

            # Generate alternative recommendations
            alternatives = await self._generate_alternatives(request, analysis_context, analysis_result)

            # Calculate overall scores
            overall_confidence, quality_score = await self._calculate_overall_scores(
                analysis_result, validation_result, alternatives
            )

            # Generate user guidance
            explanation = await self._generate_explanation(analysis_result, validation_result)
            next_steps = await self._generate_next_steps(analysis_result, validation_result)
            warnings = await self._generate_warnings(analysis_result, validation_result)

            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create response
            response = RecommendationResponse(
                request_id=request.request_id,
                success=True,
                recommendation=analysis_result,
                alternatives=alternatives,
                validation=validation_result,
                processing_time_ms=processing_time_ms,
                llm_providers_used=self._get_providers_used(analysis_result),
                consensus_achieved=len(analysis_result.consensus_providers) > 0,
                overall_confidence=overall_confidence,
                quality_score=quality_score,
                explanation=explanation,
                next_steps=next_steps,
                warnings=warnings,
                debug_info=await self._generate_debug_info(analysis_result, validation_result)
            )

            # Cache result if enabled
            if self.enable_caching:
                await self._cache_result(request, response)

            logger.info(f"AI analysis completed for request {request.request_id}: {overall_confidence:.2f} confidence")
            return response

        except Exception as e:
            logger.error(f"AI analysis failed for request {request.request_id}: {str(e)}")
            return await self._create_error_response(request, str(e), start_time)

    async def _merge_contexts(self, request_context: AnalysisContext, request: RecommendationRequest) -> AnalysisContext:
        """Merge request context with service defaults."""
        merged_context = AnalysisContext(**self.default_context.dict())

        # Update with request context
        for field, value in request_context.dict().items():
            if value is not None:
                setattr(merged_context, field, value)

        # Add request-specific information
        merged_context.max_processing_time = request.max_processing_time
        merged_context.required_confidence = request.min_confidence

        # Update user preferences from request
        if request.user_id:
            # In a real implementation, this would load user preferences from a database
            user_preferences = await self._load_user_preferences(request.user_id)
            merged_context.user_preferences.update(user_preferences)

        return merged_context

    async def _check_cache(self, request: RecommendationRequest) -> Optional[RecommendationResponse]:
        """Check if a similar request is cached."""
        # Create cache key from request data (simplified)
        cache_key = f"{request.recommendation_type.value}_{hash(str(request.data))}"

        if cache_key in self.cache:
            cached_response = self.cache[cache_key]
            # Check if cache is still valid (e.g., less than 1 hour old)
            if (datetime.utcnow() - cached_response.generated_at).seconds < 3600:
                return cached_response

        return None

    async def _run_multi_llm_analysis(
        self,
        request: RecommendationRequest,
        context: AnalysisContext,
        prompt: str
    ) -> AnalysisResult:
        """Run multi-LLM analysis with consensus building."""

        analysis_request = AnalysisRequest(
            data=request.data,
            recommendation_type=request.recommendation_type,
            context=context,
            primary_provider=request.preferred_provider,
            min_confidence=request.min_confidence,
            require_validation=True
        )

        return await self.llm_analyzer.analyze(request.data, **analysis_request.dict())

    async def _run_single_llm_analysis(
        self,
        request: RecommendationRequest,
        context: AnalysisContext,
        prompt: str
    ) -> AnalysisResult:
        """Run single LLM analysis."""

        # Create a simplified analysis request for single LLM
        analysis_request = AnalysisRequest(
            data=request.data,
            recommendation_type=request.recommendation_type,
            context=context,
            primary_provider=request.preferred_provider,
            validation_providers=[],  # No validation providers for single LLM
            enable_consensus=False,
            min_confidence=request.min_confidence
        )

        return await self.llm_analyzer.analyze(request.data, **analysis_request.dict())

    async def _apply_validation_fixes(
        self,
        result: AnalysisResult,
        validation: ValidationResult,
        context: AnalysisContext
    ) -> AnalysisResult:
        """Apply validation fixes to improve recommendation quality."""

        # Apply simple auto-fixes
        fixed_recommendation = result.primary_recommendation.copy()

        for issue in validation.issues:
            if issue.field and issue.suggestion:
                # Apply simple fixes based on validation suggestions
                if "confidence" in issue.field.lower() and "bounds" in issue.message.lower():
                    # Fix confidence score bounds
                    result.confidence_score = max(0.0, min(1.0, result.confidence_score))
                    result.confidence_level = AnalysisResult.determine_confidence_level(result.confidence_score)

                elif "chart_type" in issue.field.lower() and "data size" in issue.message.lower():
                    # Fix chart type for data size issues
                    if context.row_count > 10000:
                        fixed_recommendation["chart_type"] = "aggregated_bar"
                    elif context.row_count < 10:
                        fixed_recommendation["chart_type"] = "table"

        # Update the result with fixes
        result.primary_recommendation = fixed_recommendation
        result.validation_issues = [issue.message for issue in validation.issues]

        return result

    async def _generate_alternatives(
        self,
        request: RecommendationRequest,
        context: AnalysisContext,
        primary_result: AnalysisResult
    ) -> List[AnalysisResult]:
        """Generate alternative recommendations."""
        alternatives = []

        try:
            # Generate 2-3 alternative approaches
            alt_contexts = await self._create_alternative_contexts(context)

            for i, alt_context in enumerate(alt_contexts[:2]):  # Limit to 2 alternatives
                alt_request = AnalysisRequest(
                    data=request.data,
                    recommendation_type=request.recommendation_type,
                    context=alt_context,
                    primary_provider=request.preferred_provider,
                    enable_consensus=False,  # Faster for alternatives
                    min_confidence=request.min_confidence * 0.8  # Lower threshold for alternatives
                )

                alt_result = await self.llm_analyzer.analyze(request.data, **alt_request.dict())

                # Ensure alternative is actually different
                if alt_result.primary_recommendation != primary_result.primary_recommendation:
                    alternatives.append(alt_result)

        except Exception as e:
            logger.warning(f"Failed to generate alternatives: {str(e)}")

        return alternatives

    async def _create_alternative_contexts(self, base_context: AnalysisContext) -> List[AnalysisContext]:
        """Create alternative analysis contexts for generating diverse recommendations."""
        alternatives = []

        # Alternative 1: Different target audience
        alt1 = AnalysisContext(**base_context.dict())
        alt1.target_audience = "executives" if base_context.target_audience != "executives" else "analysts"
        alt1.user_preferences = {"complexity": "simple", "style": "professional"}
        alternatives.append(alt1)

        # Alternative 2: Different complexity preference
        alt2 = AnalysisContext(**base_context.dict())
        alt2.user_preferences = base_context.user_preferences.copy()
        alt2.user_preferences["complexity"] = "complex" if base_context.user_preferences.get("complexity") != "complex" else "simple"
        alternatives.append(alt2)

        return alternatives

    async def _calculate_overall_scores(
        self,
        result: AnalysisResult,
        validation: Optional[ValidationResult],
        alternatives: List[AnalysisResult]
    ) -> Tuple[float, float]:
        """Calculate overall confidence and quality scores."""

        # Base confidence from primary result
        confidence = result.confidence_score

        # Adjust based on validation
        if validation:
            validation_factor = validation.overall_score
            confidence = confidence * (0.7 + 0.3 * validation_factor)

        # Adjust based on alternatives (consensus increases confidence)
        if alternatives:
            consensus_factor = len(alternatives) * 0.1  # Small boost for having alternatives
            confidence = min(1.0, confidence + consensus_factor)

        # Quality score combines multiple factors
        quality_factors = []
        quality_factors.append(result.confidence_score)  # AI confidence

        if validation:
            quality_factors.append(validation.overall_score)  # Validation quality

        # Technical quality factors
        if result.analysis_time_ms < 10000:  # Fast analysis is good
            quality_factors.append(0.9)
        else:
            quality_factors.append(0.7)

        quality_score = sum(quality_factors) / len(quality_factors) if quality_factors else 0.5

        return confidence, quality_score

    async def _generate_explanation(
        self,
        result: AnalysisResult,
        validation: Optional[ValidationResult]
    ) -> str:
        """Generate human-readable explanation of the recommendation."""

        explanation_parts = [
            f"Based on analysis of your data, we recommend: {result.explanation}",
            f"This recommendation has {result.confidence_level.value} confidence ({result.confidence_score:.1%})."
        ]

        if result.reasoning:
            explanation_parts.append(f"Reasoning: {result.reasoning}")

        if validation and not validation.is_valid:
            explanation_parts.append(f"Note: {len(validation.issues)} validation points were identified and addressed.")

        if result.consensus_providers:
            explanation_parts.append(f"This recommendation was cross-validated using {len(result.consensus_providers) + 1} AI models.")

        return " ".join(explanation_parts)

    async def _generate_next_steps(
        self,
        result: AnalysisResult,
        validation: Optional[ValidationResult]
    ) -> List[str]:
        """Generate suggested next steps for the user."""
        next_steps = []

        if result.confidence_score >= 0.8:
            next_steps.append("Implement this recommendation with confidence")
        elif result.confidence_score >= 0.6:
            next_steps.append("Review the recommendation details before implementing")
        else:
            next_steps.append("Consider gathering more data or context before implementing")

        if validation and validation.suggestions:
            next_steps.extend(validation.suggestions[:2])  # Add top 2 validation suggestions

        if result.alternative_options:
            next_steps.append("Review alternative options for comparison")

        return next_steps

    async def _generate_warnings(
        self,
        result: AnalysisResult,
        validation: Optional[ValidationResult]
    ) -> List[str]:
        """Generate important warnings for the user."""
        warnings = []

        if result.confidence_score < 0.6:
            warnings.append("Low confidence recommendation - please review carefully")

        if validation:
            critical_issues = [issue for issue in validation.issues if issue.severity.value in ["critical", "error"]]
            if critical_issues:
                warnings.append(f"{len(critical_issues)} critical issues found - review before implementing")

        if not result.validation_passed:
            warnings.append("Recommendation did not pass all validation checks")

        return warnings

    async def _generate_debug_info(
        self,
        result: AnalysisResult,
        validation: Optional[ValidationResult]
    ) -> Dict[str, Any]:
        """Generate debug information for troubleshooting."""
        debug_info = {
            "llm_provider": result.llm_provider.value,
            "analysis_time_ms": result.analysis_time_ms,
            "assumptions_count": len(result.assumptions),
            "metadata_factors_count": len(result.metadata_factors)
        }

        if validation:
            debug_info.update({
                "validation_score": validation.overall_score,
                "validation_issues_count": len(validation.issues),
                "validation_time_ms": validation.validation_time_ms
            })

        return debug_info

    async def _create_error_response(
        self,
        request: RecommendationRequest,
        error: str,
        start_time: datetime
    ) -> RecommendationResponse:
        """Create error response when analysis fails."""
        end_time = datetime.utcnow()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000

        return RecommendationResponse(
            request_id=request.request_id,
            success=False,
            recommendation=None,
            validation=None,
            processing_time_ms=processing_time_ms,
            overall_confidence=0.0,
            quality_score=0.0,
            explanation=f"Analysis failed: {error}",
            next_steps=["Please check your data and try again", "Contact support if the issue persists"],
            warnings=[f"Analysis error: {error}"],
            debug_info={"error": error, "timestamp": end_time.isoformat()}
        )

    async def _load_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Load user preferences from storage."""
        # In a real implementation, this would query a database
        # For now, return empty preferences
        return {}

    async def _cache_result(self, request: RecommendationRequest, response: RecommendationResponse):
        """Cache the result for future use."""
        cache_key = f"{request.recommendation_type.value}_{hash(str(request.data))}"
        self.cache[cache_key] = response

    def _get_providers_used(self, result: AnalysisResult) -> List[LLMProvider]:
        """Get list of LLM providers used in analysis."""
        providers = [result.llm_provider]
        providers.extend(result.consensus_providers)
        return list(set(providers))  # Remove duplicates

    # Public utility methods

    async def get_supported_recommendation_types(self) -> List[RecommendationType]:
        """Get list of supported recommendation types."""
        return list(RecommendationType)

    async def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available LLM providers."""
        return list(LLMProvider)

    async def validate_request(self, request: RecommendationRequest) -> Tuple[bool, List[str]]:
        """Validate a recommendation request."""
        issues = []

        if not request.data:
            issues.append("Data is required for analysis")

        if request.min_confidence < 0 or request.min_confidence > 1:
            issues.append("Minimum confidence must be between 0 and 1")

        if request.max_processing_time < 5:
            issues.append("Processing time must be at least 5 seconds")

        return len(issues) == 0, issues

    async def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "cache_size": len(self.cache),
            "supported_types": len(list(RecommendationType)),
            "available_providers": len(list(LLMProvider)),
            "service_version": "1.0"
        }
