"""
Multi-LLM Analysis Pipeline.

This module provides the core multi-LLM analysis capabilities including:
- Primary LLM analysis with detailed prompts
- Secondary LLM validation and cross-checking
- Confidence scoring based on agreement
- Fallback rule-based recommendations
"""

import statistics
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from .base import (
    AIAnalysisInterface,
    LLMProvider,
    AnalysisContext,
    AnalysisResult,
    RecommendationType,
    ConfidenceLevel
)

logger = logging.getLogger(__name__)


class LLMAnalysisResult(BaseModel):
    """Result from a single LLM analysis."""

    provider: LLMProvider = Field(..., description="LLM provider used")
    recommendation: Dict[str, Any] = Field(..., description="LLM recommendation")
    reasoning: str = Field(..., description="LLM reasoning")
    confidence: float = Field(..., description="LLM confidence score")
    response_time_ms: float = Field(..., description="Response time")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    raw_response: str = Field(..., description="Raw LLM response")

    # Analysis metadata
    prompt_version: str = Field(default="1.0")
    temperature: float = Field(default=0.7)
    success: bool = Field(default=True)
    error_message: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Request for AI analysis."""

    data: Dict[str, Any] = Field(..., description="Data to analyze")
    recommendation_type: RecommendationType = Field(..., description="Type of analysis needed")
    context: AnalysisContext = Field(..., description="Analysis context")

    # LLM configuration
    primary_provider: LLMProvider = Field(default=LLMProvider.OPENAI_GPT4)
    validation_providers: List[LLMProvider] = Field(default_factory=lambda: [LLMProvider.ANTHROPIC_CLAUDE])
    enable_consensus: bool = Field(default=True)

    # Quality requirements
    min_confidence: float = Field(default=0.6)
    require_validation: bool = Field(default=True)
    max_attempts: int = Field(default=3)


class ConsensusBuilder:
    """Builds consensus from multiple LLM analyses."""

    def __init__(self):
        self.agreement_threshold = 0.7
        self.confidence_weights = {
            LLMProvider.OPENAI_GPT4: 1.0,
            LLMProvider.ANTHROPIC_CLAUDE: 0.9,
            LLMProvider.GOOGLE_GEMINI: 0.8,
            LLMProvider.OPENAI_GPT35: 0.7
        }

    async def build_consensus(self, results: List[LLMAnalysisResult]) -> Tuple[Dict[str, Any], float, str]:
        """
        Build consensus from multiple LLM results.

        Returns:
            Tuple of (consensus_recommendation, confidence_score, reasoning)
        """
        if not results:
            raise ValueError("No LLM results provided for consensus building")

        if len(results) == 1:
            result = results[0]
            return result.recommendation, result.confidence, result.reasoning

        # Calculate weighted agreement
        agreement_scores = await self._calculate_agreement_scores(results)

        # Select best recommendation based on weighted consensus
        best_result = await self._select_best_recommendation(results, agreement_scores)

        # Calculate consensus confidence
        consensus_confidence = await self._calculate_consensus_confidence(results, agreement_scores)

        # Generate consensus reasoning
        consensus_reasoning = await self._generate_consensus_reasoning(results, best_result)

        return best_result.recommendation, consensus_confidence, consensus_reasoning

    async def _calculate_agreement_scores(self, results: List[LLMAnalysisResult]) -> Dict[str, float]:
        """Calculate agreement scores between LLM results."""
        agreement_scores = {}

        for i, result in enumerate(results):
            agreements = []

            for j, other_result in enumerate(results):
                if i != j:
                    # Calculate semantic similarity between recommendations
                    similarity = await self._calculate_similarity(
                        result.recommendation,
                        other_result.recommendation
                    )
                    agreements.append(similarity)

            agreement_scores[f"result_{i}"] = statistics.mean(agreements) if agreements else 1.0

        return agreement_scores

    async def _calculate_similarity(self, rec1: Dict[str, Any], rec2: Dict[str, Any]) -> float:
        """Calculate similarity between two recommendations."""
        # Simple similarity calculation based on overlapping keys and values
        if not rec1 or not rec2:
            return 0.0

        common_keys = set(rec1.keys()) & set(rec2.keys())
        if not common_keys:
            return 0.0

        matches = 0
        total = len(common_keys)

        for key in common_keys:
            if rec1[key] == rec2[key]:
                matches += 1
            elif isinstance(rec1[key], (int, float)) and isinstance(rec2[key], (int, float)):
                # For numeric values, consider them similar if within 20%
                diff = abs(rec1[key] - rec2[key]) / max(abs(rec1[key]), abs(rec2[key]), 1)
                if diff < 0.2:
                    matches += 0.8

        return matches / total if total > 0 else 0.0

    async def _select_best_recommendation(self, results: List[LLMAnalysisResult], agreement_scores: Dict[str, float]) -> LLMAnalysisResult:
        """Select the best recommendation based on agreement and provider weight."""
        best_score = 0.0
        best_result = results[0]

        for i, result in enumerate(results):
            # Combine agreement score, confidence, and provider weight
            provider_weight = self.confidence_weights.get(result.provider, 0.5)
            agreement_score = agreement_scores.get(f"result_{i}", 0.0)

            combined_score = (
                result.confidence * 0.4 +
                agreement_score * 0.4 +
                provider_weight * 0.2
            )

            if combined_score > best_score:
                best_score = combined_score
                best_result = result

        return best_result

    async def _calculate_consensus_confidence(self, results: List[LLMAnalysisResult], agreement_scores: Dict[str, float]) -> float:
        """Calculate overall consensus confidence."""
        # Average confidence weighted by agreement
        weighted_confidences = []

        for i, result in enumerate(results):
            agreement = agreement_scores.get(f"result_{i}", 0.0)
            provider_weight = self.confidence_weights.get(result.provider, 0.5)

            weighted_confidence = result.confidence * agreement * provider_weight
            weighted_confidences.append(weighted_confidence)

        return statistics.mean(weighted_confidences) if weighted_confidences else 0.0

    async def _generate_consensus_reasoning(self, results: List[LLMAnalysisResult], best_result: LLMAnalysisResult) -> str:
        """Generate reasoning explaining the consensus."""
        reasoning_parts = [
            f"Consensus analysis based on {len(results)} LLM providers.",
            f"Primary recommendation from {best_result.provider.value}.",
            best_result.reasoning
        ]

        # Add agreement analysis
        provider_names = [r.provider.value for r in results]
        reasoning_parts.append(f"Cross-validated with: {', '.join(provider_names)}")

        return " ".join(reasoning_parts)


class MultiLLMAnalyzer(AIAnalysisInterface):
    """Multi-LLM analyzer that provides reliable insights through consensus."""

    def __init__(self, context: Optional[AnalysisContext] = None):
        super().__init__(context)
        self.consensus_builder = ConsensusBuilder()
        self.fallback_rules = self._load_fallback_rules()

    async def analyze(self, data: Any, **kwargs) -> AnalysisResult:
        """
        Perform multi-LLM analysis with consensus building.

        Args:
            data: Data to analyze
            **kwargs: Additional analysis options

        Returns:
            AnalysisResult with consensus recommendation
        """
        try:
            start_time = datetime.utcnow()

            # Create analysis request
            request = AnalysisRequest(
                data=data if isinstance(data, dict) else {"raw_data": data},
                recommendation_type=kwargs.get('recommendation_type', RecommendationType.CHART_TYPE),
                context=self.context,
                **{k: v for k, v in kwargs.items() if k != 'recommendation_type'}
            )

            # Run primary LLM analysis
            primary_result = await self._run_primary_analysis(request)

            # Run validation analyses if enabled
            validation_results = []
            if request.require_validation:
                validation_results = await self._run_validation_analyses(request)

            # Build consensus
            all_results = [primary_result] + validation_results
            consensus_rec, consensus_conf, consensus_reasoning = await self.consensus_builder.build_consensus(all_results)

            # Apply fallback rules if confidence is too low
            if consensus_conf < request.min_confidence:
                logger.warning(f"Consensus confidence {consensus_conf:.2f} below threshold {request.min_confidence}")
                consensus_rec, consensus_conf, consensus_reasoning = await self._apply_fallback_rules(request, all_results)

            # Calculate analysis time
            end_time = datetime.utcnow()
            analysis_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create final result
            result = AnalysisResult(
                recommendation_type=request.recommendation_type,
                primary_recommendation=consensus_rec,
                alternative_options=[r.recommendation for r in all_results[1:]] if len(all_results) > 1 else [],
                confidence_score=consensus_conf,
                confidence_level=AnalysisResult.determine_confidence_level(consensus_conf),
                reasoning=consensus_reasoning,
                explanation=await self._generate_explanation(consensus_rec, request.recommendation_type),
                llm_provider=primary_result.provider,
                consensus_providers=[r.provider for r in validation_results],
                analysis_time_ms=analysis_time_ms,
                supporting_data={
                    "llm_results": [r.dict() for r in all_results],
                    "consensus_method": "weighted_agreement"
                }
            )

            # Validate final result
            result.validation_passed = await self.validate_result(result)

            logger.info(f"Multi-LLM analysis completed: {result.confidence_level.value} confidence")
            return result

        except Exception as e:
            logger.error(f"Multi-LLM analysis failed: {str(e)}")
            # Return fallback result
            return await self._create_fallback_result(kwargs.get('recommendation_type', RecommendationType.CHART_TYPE), str(e))

    async def _run_primary_analysis(self, request: AnalysisRequest) -> LLMAnalysisResult:
        """Run primary LLM analysis."""
        start_time = datetime.utcnow()

        try:
            # This would integrate with actual LLM providers
            # For now, we'll simulate the analysis
            recommendation = await self._simulate_llm_analysis(request, request.primary_provider)

            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000

            return LLMAnalysisResult(
                provider=request.primary_provider,
                recommendation=recommendation,
                reasoning=f"Analysis based on {request.recommendation_type.value} requirements and data characteristics",
                confidence=0.8,  # Simulated confidence
                response_time_ms=response_time,
                raw_response=f"Simulated {request.primary_provider.value} response"
            )

        except Exception as e:
            logger.error(f"Primary analysis failed: {str(e)}")
            raise

    async def _run_validation_analyses(self, request: AnalysisRequest) -> List[LLMAnalysisResult]:
        """Run validation analyses with secondary LLMs."""
        validation_results = []

        for provider in request.validation_providers:
            try:
                start_time = datetime.utcnow()

                recommendation = await self._simulate_llm_analysis(request, provider)

                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000

                result = LLMAnalysisResult(
                    provider=provider,
                    recommendation=recommendation,
                    reasoning=f"Validation analysis from {provider.value}",
                    confidence=0.75,  # Simulated confidence
                    response_time_ms=response_time,
                    raw_response=f"Simulated {provider.value} validation response"
                )

                validation_results.append(result)

            except Exception as e:
                logger.warning(f"Validation analysis failed for {provider.value}: {str(e)}")

        return validation_results

    async def _simulate_llm_analysis(self, request: AnalysisRequest, provider: LLMProvider) -> Dict[str, Any]:
        """Simulate LLM analysis (to be replaced with real LLM integration)."""
        # Simulate different recommendations based on type
        if request.recommendation_type == RecommendationType.CHART_TYPE:
            return {
                "chart_type": "bar",
                "reasoning": "Bar charts work well for categorical data comparison",
                "confidence": 0.8
            }
        elif request.recommendation_type == RecommendationType.COLOR_SCHEME:
            return {
                "color_scheme": "blue_gradient",
                "colors": ["#1f77b4", "#aec7e8", "#ffbb78"],
                "reasoning": "Blue gradient provides good contrast and accessibility"
            }
        else:
            return {
                "recommendation": f"Recommended approach for {request.recommendation_type.value}",
                "reasoning": "Based on data analysis and best practices"
            }

    async def _apply_fallback_rules(self, request: AnalysisRequest, results: List[LLMAnalysisResult]) -> Tuple[Dict[str, Any], float, str]:
        """Apply rule-based fallback recommendations."""
        logger.info("Applying fallback rules due to low confidence")

        fallback_rec = self.fallback_rules.get(
            request.recommendation_type.value,
            {"recommendation": "default", "reasoning": "Rule-based fallback"}
        )

        return fallback_rec, 0.6, "Rule-based recommendation applied due to low LLM consensus"

    async def _generate_explanation(self, recommendation: Dict[str, Any], rec_type: RecommendationType) -> str:
        """Generate human-readable explanation of the recommendation."""
        base_explanation = f"Based on analysis of your data, we recommend: {recommendation}"

        type_specific = {
            RecommendationType.CHART_TYPE: "This chart type will best represent your data patterns and make insights clear to your audience.",
            RecommendationType.COLOR_SCHEME: "This color scheme ensures good readability and visual appeal while maintaining accessibility standards.",
            RecommendationType.LAYOUT_DESIGN: "This layout organizes your content for optimal user experience and information flow."
        }

        return base_explanation + " " + type_specific.get(rec_type, "This approach follows data visualization best practices.")

    async def _create_fallback_result(self, rec_type: RecommendationType, error: str) -> AnalysisResult:
        """Create a fallback result when analysis fails."""
        return AnalysisResult(
            recommendation_type=rec_type,
            primary_recommendation={"fallback": True, "error": error},
            confidence_score=0.3,
            confidence_level=ConfidenceLevel.LOW,
            reasoning="Fallback recommendation due to analysis failure",
            explanation="Unable to perform full AI analysis, using default recommendation",
            llm_provider=LLMProvider.OPENAI_GPT4,
            validation_passed=False,
            validation_issues=[f"Analysis failed: {error}"]
        )

    async def validate_result(self, result: AnalysisResult) -> bool:
        """Validate the analysis result for quality and consistency."""
        try:
            # Check basic result validity
            if not result.primary_recommendation:
                return False

            if result.confidence_score < 0 or result.confidence_score > 1:
                return False

            # Check if recommendation makes sense for the type
            return True

        except Exception as e:
            logger.error(f"Result validation failed: {str(e)}")
            return False

    def _load_fallback_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load rule-based fallback recommendations."""
        return {
            "chart_type": {
                "chart_type": "column",
                "reasoning": "Column charts are versatile and work well for most data types"
            },
            "color_scheme": {
                "color_scheme": "default",
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c"],
                "reasoning": "Standard color palette with good contrast"
            },
            "layout_design": {
                "layout": "grid",
                "reasoning": "Grid layout provides clear organization"
            }
        }
