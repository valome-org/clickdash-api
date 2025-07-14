"""
Recommendation Validation System.

This module ensures AI recommendations make sense through:
- Logical consistency checking
- Data appropriateness validation
- Visual design principle compliance
- User goal alignment verification
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import logging

from .base import AnalysisResult, RecommendationType, AnalysisContext

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(str, Enum):
    """Categories of validation checks."""
    LOGICAL_CONSISTENCY = "logical_consistency"
    DATA_APPROPRIATENESS = "data_appropriateness"
    DESIGN_PRINCIPLES = "design_principles"
    USER_ALIGNMENT = "user_alignment"
    TECHNICAL_FEASIBILITY = "technical_feasibility"
    ACCESSIBILITY = "accessibility"


class ValidationIssue(BaseModel):
    """Individual validation issue."""

    category: ValidationCategory = Field(..., description="Issue category")
    severity: ValidationSeverity = Field(..., description="Issue severity")
    message: str = Field(..., description="Issue description")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    field: Optional[str] = Field(None, description="Affected field")
    confidence: float = Field(default=1.0, description="Confidence in this issue")


class ValidationRule(BaseModel):
    """Definition of a validation rule."""

    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    category: ValidationCategory = Field(..., description="Rule category")
    description: str = Field(..., description="Rule description")

    # Rule conditions
    applies_to: List[RecommendationType] = Field(..., description="Applicable recommendation types")
    required_fields: List[str] = Field(default_factory=list, description="Required fields in recommendation")

    # Rule behavior
    severity: ValidationSeverity = Field(default=ValidationSeverity.WARNING)
    enabled: bool = Field(default=True)
    auto_fix: bool = Field(default=False, description="Whether this rule can auto-fix issues")

    # Rule metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")


class ValidationResult(BaseModel):
    """Result of validation operation."""

    is_valid: bool = Field(..., description="Overall validation status")
    overall_score: float = Field(..., description="Overall validation score (0.0-1.0)")

    # Issues breakdown
    issues: List[ValidationIssue] = Field(default_factory=list)
    critical_count: int = Field(default=0)
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    info_count: int = Field(default=0)

    # Category scores
    category_scores: Dict[str, float] = Field(default_factory=dict)

    # Recommendations
    auto_fixes: List[str] = Field(default_factory=list, description="Available auto-fixes")
    suggestions: List[str] = Field(default_factory=list, description="Manual improvement suggestions")

    # Validation metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validation_time_ms: float = Field(default=0.0)
    rules_applied: int = Field(default=0)


class LogicalConsistencyChecker:
    """Checks logical consistency of AI recommendations."""

    def __init__(self):
        self.consistency_rules = self._load_consistency_rules()

    async def check_consistency(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> List[ValidationIssue]:
        """Check logical consistency of the analysis result."""
        issues = []

        # Check recommendation type consistency
        issues.extend(await self._check_recommendation_type_consistency(result))

        # Check confidence consistency
        issues.extend(await self._check_confidence_consistency(result))

        # Check assumption consistency
        issues.extend(await self._check_assumption_consistency(result))

        # Check alternative options consistency
        issues.extend(await self._check_alternatives_consistency(result))

        return issues

    async def _check_recommendation_type_consistency(self, result: AnalysisResult) -> List[ValidationIssue]:
        """Check if recommendation content matches the recommendation type."""
        issues = []
        rec = result.primary_recommendation
        rec_type = result.recommendation_type

        # Define expected fields for each recommendation type
        expected_fields = {
            RecommendationType.CHART_TYPE: ['chart_type', 'reasoning'],
            RecommendationType.COLOR_SCHEME: ['colors', 'color_scheme'],
            RecommendationType.LAYOUT_DESIGN: ['layout', 'layout_type'],
            RecommendationType.DATA_AGGREGATION: ['aggregation_method', 'grouping'],
            RecommendationType.FILTERING: ['filters', 'filter_criteria']
        }

        required_fields = expected_fields.get(rec_type, [])
        for field in required_fields:
            if field not in rec:
                issues.append(ValidationIssue(
                    category=ValidationCategory.LOGICAL_CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required field '{field}' for {rec_type.value} recommendation",
                    suggestion=f"Add '{field}' field to recommendation",
                    field=field
                ))

        return issues

    async def _check_confidence_consistency(self, result: AnalysisResult) -> List[ValidationIssue]:
        """Check if confidence scores are consistent."""
        issues = []

        # Check confidence score bounds
        if not (0.0 <= result.confidence_score <= 1.0):
            issues.append(ValidationIssue(
                category=ValidationCategory.LOGICAL_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                message=f"Confidence score {result.confidence_score} is out of bounds [0.0, 1.0]",
                suggestion="Ensure confidence score is between 0.0 and 1.0",
                field="confidence_score"
            ))

        # Check consistency with confidence level
        expected_level = AnalysisResult.determine_confidence_level(result.confidence_score)
        if result.confidence_level != expected_level:
            issues.append(ValidationIssue(
                category=ValidationCategory.LOGICAL_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                message=f"Confidence level '{result.confidence_level}' doesn't match score {result.confidence_score}",
                suggestion=f"Update confidence level to '{expected_level}'",
                field="confidence_level"
            ))

        return issues

    async def _check_assumption_consistency(self, result: AnalysisResult) -> List[ValidationIssue]:
        """Check if assumptions are reasonable and documented."""
        issues = []

        # Check if high-confidence results have documented assumptions
        if result.confidence_score > 0.8 and not result.assumptions:
            issues.append(ValidationIssue(
                category=ValidationCategory.LOGICAL_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                message="High-confidence recommendation lacks documented assumptions",
                suggestion="Document key assumptions made during analysis",
                field="assumptions"
            ))

        # Check for contradictory assumptions
        assumptions_text = " ".join(result.assumptions).lower()
        contradictions = [
            ("small dataset", "large dataset"),
            ("simple", "complex"),
            ("low quality", "high quality")
        ]

        for term1, term2 in contradictions:
            if term1 in assumptions_text and term2 in assumptions_text:
                issues.append(ValidationIssue(
                    category=ValidationCategory.LOGICAL_CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    message=f"Contradictory assumptions: '{term1}' and '{term2}'",
                    suggestion="Review and resolve contradictory assumptions",
                    field="assumptions"
                ))

        return issues

    async def _check_alternatives_consistency(self, result: AnalysisResult) -> List[ValidationIssue]:
        """Check consistency of alternative options."""
        issues = []

        # Check if alternatives are actually different from primary
        primary = result.primary_recommendation
        for i, alt in enumerate(result.alternative_options):
            if alt == primary:
                issues.append(ValidationIssue(
                    category=ValidationCategory.LOGICAL_CONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    message=f"Alternative option {i+1} is identical to primary recommendation",
                    suggestion="Ensure alternatives provide meaningful different options",
                    field="alternative_options"
                ))

        return issues

    def _load_consistency_rules(self) -> List[ValidationRule]:
        """Load logical consistency rules."""
        return [
            ValidationRule(
                rule_id="consistency_rec_type_fields",
                name="Recommendation Type Field Consistency",
                category=ValidationCategory.LOGICAL_CONSISTENCY,
                description="Recommendation must contain fields appropriate for its type",
                applies_to=list(RecommendationType),
                severity=ValidationSeverity.ERROR
            ),
            ValidationRule(
                rule_id="consistency_confidence_bounds",
                name="Confidence Score Bounds",
                category=ValidationCategory.LOGICAL_CONSISTENCY,
                description="Confidence score must be between 0.0 and 1.0",
                applies_to=list(RecommendationType),
                severity=ValidationSeverity.ERROR
            )
        ]


class DataAppropriatenessValidator:
    """Validates that recommendations are appropriate for the data."""

    def __init__(self):
        self.data_rules = self._load_data_rules()

    async def validate_data_appropriateness(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> List[ValidationIssue]:
        """Validate that recommendations are appropriate for the data characteristics."""
        issues = []

        # Check data size appropriateness
        issues.extend(await self._check_data_size_appropriateness(result, context))

        # Check data type compatibility
        issues.extend(await self._check_data_type_compatibility(result, context))

        # Check aggregation appropriateness
        issues.extend(await self._check_aggregation_appropriateness(result, context))

        return issues

    async def _check_data_size_appropriateness(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> List[ValidationIssue]:
        """Check if recommendation is appropriate for data size."""
        issues = []
        rec = result.primary_recommendation

        # Chart type recommendations based on data size
        if result.recommendation_type == RecommendationType.CHART_TYPE:
            chart_type = rec.get('chart_type', '')

            # Too much data for detailed charts
            if context.row_count > 10000:
                detailed_charts = ['scatter', 'line', 'area']
                if chart_type in detailed_charts:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DATA_APPROPRIATENESS,
                        severity=ValidationSeverity.WARNING,
                        message=f"Chart type '{chart_type}' may not be suitable for large dataset ({context.row_count} rows)",
                        suggestion="Consider aggregation or sampling for large datasets",
                        field="chart_type"
                    ))

            # Too little data for statistical charts
            if context.row_count < 10:
                statistical_charts = ['histogram', 'box_plot', 'violin']
                if chart_type in statistical_charts:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DATA_APPROPRIATENESS,
                        severity=ValidationSeverity.ERROR,
                        message=f"Chart type '{chart_type}' requires more data (current: {context.row_count} rows)",
                        suggestion="Use bar or column charts for small datasets",
                        field="chart_type"
                    ))

        return issues

    async def _check_data_type_compatibility(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> List[ValidationIssue]:
        """Check if recommendation is compatible with data types."""
        issues = []
        rec = result.primary_recommendation

        # Get data type counts
        data_types = context.data_types
        type_counts = {}
        for dtype in data_types.values():
            type_counts[dtype] = type_counts.get(dtype, 0) + 1

        if result.recommendation_type == RecommendationType.CHART_TYPE:
            chart_type = rec.get('chart_type', '')

            # Numeric data requirements
            numeric_charts = ['histogram', 'scatter', 'line', 'area']
            if chart_type in numeric_charts and type_counts.get('numeric', 0) == 0:
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_APPROPRIATENESS,
                    severity=ValidationSeverity.ERROR,
                    message=f"Chart type '{chart_type}' requires numeric data",
                    suggestion="Use bar or pie charts for categorical data",
                    field="chart_type"
                ))

            # Categorical data requirements
            categorical_charts = ['pie', 'donut']
            if chart_type in categorical_charts and type_counts.get('categorical', 0) == 0:
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_APPROPRIATENESS,
                    severity=ValidationSeverity.WARNING,
                    message=f"Chart type '{chart_type}' works better with categorical data",
                    suggestion="Consider bar charts for non-categorical data",
                    field="chart_type"
                ))

        return issues

    async def _check_aggregation_appropriateness(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> List[ValidationIssue]:
        """Check if aggregation recommendations are appropriate."""
        issues = []

        if result.recommendation_type == RecommendationType.DATA_AGGREGATION:
            rec = result.primary_recommendation
            agg_method = rec.get('aggregation_method', '')

            # Check if aggregation method is appropriate for data types
            numeric_aggregations = ['sum', 'average', 'median', 'std']
            if agg_method in numeric_aggregations:
                numeric_columns = [col for col, dtype in context.data_types.items() if 'numeric' in dtype or 'int' in dtype or 'float' in dtype]
                if not numeric_columns:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DATA_APPROPRIATENESS,
                        severity=ValidationSeverity.ERROR,
                        message=f"Aggregation method '{agg_method}' requires numeric data",
                        suggestion="Use 'count' or 'distinct_count' for categorical data",
                        field="aggregation_method"
                    ))

        return issues

    def _load_data_rules(self) -> List[ValidationRule]:
        """Load data appropriateness rules."""
        return [
            ValidationRule(
                rule_id="data_size_chart_appropriateness",
                name="Data Size Chart Appropriateness",
                category=ValidationCategory.DATA_APPROPRIATENESS,
                description="Chart types must be appropriate for data size",
                applies_to=[RecommendationType.CHART_TYPE],
                severity=ValidationSeverity.WARNING
            ),
            ValidationRule(
                rule_id="data_type_compatibility",
                name="Data Type Compatibility",
                category=ValidationCategory.DATA_APPROPRIATENESS,
                description="Recommendations must be compatible with data types",
                applies_to=list(RecommendationType),
                severity=ValidationSeverity.ERROR
            )
        ]


class DesignPrincipleValidator:
    """Validates recommendations against visual design principles."""

    def __init__(self):
        self.design_rules = self._load_design_rules()

    async def validate_design_principles(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> List[ValidationIssue]:
        """Validate recommendations against design principles."""
        issues = []

        # Check color accessibility
        issues.extend(await self._check_color_accessibility(result))

        # Check visual hierarchy
        issues.extend(await self._check_visual_hierarchy(result))

        # Check cognitive load
        issues.extend(await self._check_cognitive_load(result, context))

        return issues

    async def _check_color_accessibility(self, result: AnalysisResult) -> List[ValidationIssue]:
        """Check color accessibility compliance."""
        issues = []

        if result.recommendation_type == RecommendationType.COLOR_SCHEME:
            rec = result.primary_recommendation
            colors = rec.get('colors', [])

            # Check for accessibility issues
            if len(colors) > 1:
                # Check for red-green combinations (colorblind unfriendly)
                color_names = [c.lower() for c in colors if isinstance(c, str)]
                if 'red' in color_names and 'green' in color_names:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.ACCESSIBILITY,
                        severity=ValidationSeverity.WARNING,
                        message="Red-green color combination may be problematic for colorblind users",
                        suggestion="Consider using blue-orange or other colorblind-friendly combinations",
                        field="colors"
                    ))

                # Check for too many similar colors
                if len(set(color_names)) < len(color_names) * 0.7:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DESIGN_PRINCIPLES,
                        severity=ValidationSeverity.WARNING,
                        message="Color scheme contains too many similar colors",
                        suggestion="Use more distinct colors for better differentiation",
                        field="colors"
                    ))

        return issues

    async def _check_visual_hierarchy(self, result: AnalysisResult) -> List[ValidationIssue]:
        """Check visual hierarchy principles."""
        issues = []

        if result.recommendation_type == RecommendationType.LAYOUT_DESIGN:
            rec = result.primary_recommendation
            layout = rec.get('layout', {})

            # Check for proper hierarchy
            if isinstance(layout, dict):
                components = layout.get('components', [])
                if len(components) > 5:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DESIGN_PRINCIPLES,
                        severity=ValidationSeverity.WARNING,
                        message="Layout has too many components for clear visual hierarchy",
                        suggestion="Group related components or reduce total number",
                        field="layout"
                    ))

        return issues

    async def _check_cognitive_load(self, result: AnalysisResult, context: AnalysisContext) -> List[ValidationIssue]:
        """Check cognitive load of recommendations."""
        issues = []

        # Check complexity vs user experience
        user_prefs = context.user_preferences
        complexity_pref = user_prefs.get('complexity', 'moderate')

        rec = result.primary_recommendation

        # Assess complexity based on recommendation
        complexity_indicators = 0
        if isinstance(rec, dict):
            if len(rec) > 5:  # Many options
                complexity_indicators += 1
            if any(isinstance(v, dict) for v in rec.values()):  # Nested structures
                complexity_indicators += 1
            if any(isinstance(v, list) and len(v) > 3 for v in rec.values()):  # Long lists
                complexity_indicators += 1

        # Check alignment with user preference
        if complexity_pref == 'simple' and complexity_indicators > 1:
            issues.append(ValidationIssue(
                category=ValidationCategory.USER_ALIGNMENT,
                severity=ValidationSeverity.WARNING,
                message="Recommendation may be too complex for user preference",
                suggestion="Simplify recommendation or provide stepped approach",
                field="primary_recommendation"
            ))
        elif complexity_pref == 'complex' and complexity_indicators == 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.USER_ALIGNMENT,
                severity=ValidationSeverity.INFO,
                message="Recommendation may be too simple for advanced user",
                suggestion="Consider providing more detailed options",
                field="primary_recommendation"
            ))

        return issues

    def _load_design_rules(self) -> List[ValidationRule]:
        """Load design principle rules."""
        return [
            ValidationRule(
                rule_id="color_accessibility",
                name="Color Accessibility",
                category=ValidationCategory.ACCESSIBILITY,
                description="Colors must be accessible to all users",
                applies_to=[RecommendationType.COLOR_SCHEME],
                severity=ValidationSeverity.WARNING
            ),
            ValidationRule(
                rule_id="visual_hierarchy",
                name="Visual Hierarchy",
                category=ValidationCategory.DESIGN_PRINCIPLES,
                description="Layout must maintain clear visual hierarchy",
                applies_to=[RecommendationType.LAYOUT_DESIGN],
                severity=ValidationSeverity.WARNING
            )
        ]


class RecommendationValidator:
    """Main recommendation validator that coordinates all validation checks."""

    def __init__(self):
        self.consistency_checker = LogicalConsistencyChecker()
        self.data_validator = DataAppropriatenessValidator()
        self.design_validator = DesignPrincipleValidator()
        self.validation_rules = self._load_all_rules()

    async def validate_recommendation(
        self,
        result: AnalysisResult,
        context: AnalysisContext
    ) -> ValidationResult:
        """
        Perform comprehensive validation of AI recommendation.

        Args:
            result: Analysis result to validate
            context: Analysis context

        Returns:
            ValidationResult with detailed validation information
        """
        try:
            start_time = datetime.utcnow()
            all_issues = []

            # Run logical consistency checks
            consistency_issues = await self.consistency_checker.check_consistency(result, context)
            all_issues.extend(consistency_issues)

            # Run data appropriateness checks
            data_issues = await self.data_validator.validate_data_appropriateness(result, context)
            all_issues.extend(data_issues)

            # Run design principle checks
            design_issues = await self.design_validator.validate_design_principles(result, context)
            all_issues.extend(design_issues)

            # Count issues by severity
            critical_count = sum(1 for issue in all_issues if issue.severity == ValidationSeverity.CRITICAL)
            error_count = sum(1 for issue in all_issues if issue.severity == ValidationSeverity.ERROR)
            warning_count = sum(1 for issue in all_issues if issue.severity == ValidationSeverity.WARNING)
            info_count = sum(1 for issue in all_issues if issue.severity == ValidationSeverity.INFO)

            # Calculate category scores
            category_scores = await self._calculate_category_scores(all_issues)

            # Calculate overall score
            overall_score = await self._calculate_overall_score(all_issues, category_scores)

            # Determine if valid (no critical or error issues)
            is_valid = critical_count == 0 and error_count == 0

            # Generate auto-fixes and suggestions
            auto_fixes = await self._generate_auto_fixes(all_issues)
            suggestions = await self._generate_suggestions(all_issues)

            # Calculate validation time
            end_time = datetime.utcnow()
            validation_time_ms = (end_time - start_time).total_seconds() * 1000

            validation_result = ValidationResult(
                is_valid=is_valid,
                overall_score=overall_score,
                issues=all_issues,
                critical_count=critical_count,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
                category_scores=category_scores,
                auto_fixes=auto_fixes,
                suggestions=suggestions,
                validation_time_ms=validation_time_ms,
                rules_applied=len(self.validation_rules)
            )

            logger.info(f"Validation completed: {len(all_issues)} issues found, score: {overall_score:.2f}")
            return validation_result

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                overall_score=0.0,
                issues=[ValidationIssue(
                    category=ValidationCategory.TECHNICAL_FEASIBILITY,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Validation system error: {str(e)}",
                    suggestion="Review validation system configuration",
                    field=None
                )]
            )

    async def _calculate_category_scores(self, issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate scores for each validation category."""
        category_scores = {}

        # Initialize all categories
        for category in ValidationCategory:
            category_scores[category.value] = 1.0

        # Reduce scores based on issues
        for issue in issues:
            current_score = category_scores[issue.category.value]

            # Penalty based on severity
            penalty = {
                ValidationSeverity.CRITICAL: 0.5,
                ValidationSeverity.ERROR: 0.3,
                ValidationSeverity.WARNING: 0.1,
                ValidationSeverity.INFO: 0.05
            }.get(issue.severity, 0.1)

            # Apply penalty with confidence weighting
            weighted_penalty = penalty * issue.confidence
            category_scores[issue.category.value] = max(0.0, current_score - weighted_penalty)

        return category_scores

    async def _calculate_overall_score(self, issues: List[ValidationIssue], category_scores: Dict[str, float]) -> float:
        """Calculate overall validation score."""
        if not category_scores:
            return 1.0

        # Weight categories by importance
        category_weights = {
            ValidationCategory.LOGICAL_CONSISTENCY.value: 0.3,
            ValidationCategory.DATA_APPROPRIATENESS.value: 0.25,
            ValidationCategory.DESIGN_PRINCIPLES.value: 0.2,
            ValidationCategory.USER_ALIGNMENT.value: 0.15,
            ValidationCategory.TECHNICAL_FEASIBILITY.value: 0.05,
            ValidationCategory.ACCESSIBILITY.value: 0.05
        }

        weighted_score = 0.0
        total_weight = 0.0

        for category, score in category_scores.items():
            weight = category_weights.get(category, 0.1)
            weighted_score += score * weight
            total_weight += weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    async def _generate_auto_fixes(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate auto-fix suggestions for fixable issues."""
        auto_fixes = []

        for issue in issues:
            if issue.suggestion and issue.severity in [ValidationSeverity.WARNING, ValidationSeverity.INFO]:
                auto_fixes.append(f"Auto-fix: {issue.suggestion}")

        return auto_fixes

    async def _generate_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate manual improvement suggestions."""
        suggestions = []

        # Group suggestions by category
        category_suggestions = {}
        for issue in issues:
            if issue.suggestion:
                category = issue.category.value
                if category not in category_suggestions:
                    category_suggestions[category] = []
                category_suggestions[category].append(issue.suggestion)

        # Create summary suggestions
        for category, cat_suggestions in category_suggestions.items():
            if len(cat_suggestions) > 1:
                suggestions.append(f"For {category}: Review {len(cat_suggestions)} validation points")
            else:
                suggestions.append(f"For {category}: {cat_suggestions[0]}")

        return suggestions

    def _load_all_rules(self) -> List[ValidationRule]:
        """Load all validation rules from all validators."""
        rules = []
        rules.extend(self.consistency_checker.consistency_rules)
        rules.extend(self.data_validator.data_rules)
        rules.extend(self.design_validator.design_rules)
        return rules
