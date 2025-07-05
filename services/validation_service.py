"""
Unified validation service that coordinates all validation operations.

This service provides a single interface for all validation functionality including:
- Schema validation and evolution tracking
- Business rule validation
- Data profiling and analysis
- Comprehensive validation reporting
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field
import uuid

from core.validation import (
    SchemaValidator,
    SchemaValidationResult,
    SchemaEvolutionTracker,
    SchemaCompatibilityChecker,
    BusinessRuleEngine,
    RuleValidationResult,
    DataProfiler,
    ProfileResult,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationContext,
    Schema,
    BusinessRule,
    IndustryTemplates
)


class ValidationRequest(BaseModel):
    """Request for comprehensive validation."""

    data: Optional[Any] = Field(None, description="Data to validate (will be converted to DataFrame)")
    validation_types: List[str] = Field(default_factory=lambda: ["schema", "rules", "profile"],
                                      description="Types of validation to perform")
    schema_id: Optional[str] = Field(None, description="Specific schema to validate against")
    rule_categories: Optional[List[str]] = Field(None, description="Specific rule categories to apply")
    context: Optional[Dict[str, Any]] = Field(None, description="Validation context")
    options: Dict[str, Any] = Field(default_factory=dict, description="Validation options")


class ValidationReport(BaseModel):
    """Comprehensive validation report combining all validation results."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Report ID")
    dataset_name: str = Field(..., description="Name of validated dataset")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")

    # Overall results
    overall_valid: bool = Field(..., description="Overall validation status")
    total_issues: int = Field(default=0, description="Total number of issues found")
    severity_summary: Dict[str, int] = Field(default_factory=dict, description="Issue count by severity")

    # Individual validation results
    schema_validation: Optional[SchemaValidationResult] = Field(None, description="Schema validation results")
    rule_validation: Optional[RuleValidationResult] = Field(None, description="Business rule validation results")
    profiling_results: Optional[ProfileResult] = Field(None, description="Data profiling results")

    # Aggregated insights
    data_quality_score: float = Field(default=0.0, description="Overall data quality score (0-100)")
    recommendations: List[str] = Field(default_factory=list, description="Consolidated recommendations")

    # Performance metrics
    total_execution_time_ms: float = Field(default=0.0, description="Total validation time")
    validation_performance: Dict[str, float] = Field(default_factory=dict, description="Performance by validation type")


class ValidationService:
    """Unified validation service coordinating all validation operations."""

    def __init__(self):
        # Initialize validators
        self.schema_validator = SchemaValidator()
        self.business_rule_engine = BusinessRuleEngine()
        self.data_profiler = DataProfiler()

        # Initialize supporting components
        self.schema_tracker = SchemaEvolutionTracker()
        self.compatibility_checker = SchemaCompatibilityChecker()

        # Load industry templates
        self._load_industry_templates()

        # Validation history
        self.validation_history: List[ValidationReport] = []

    def _load_industry_templates(self):
        """Load industry-specific rule templates."""
        # Load financial rules
        financial_template = IndustryTemplates.get_financial_template()
        for rule in financial_template.rules:
            self.business_rule_engine.add_rule(rule)

        # Load healthcare rules
        healthcare_template = IndustryTemplates.get_healthcare_template()
        for rule in healthcare_template.rules:
            self.business_rule_engine.add_rule(rule)

        # Load retail rules
        retail_template = IndustryTemplates.get_retail_template()
        for rule in retail_template.rules:
            self.business_rule_engine.add_rule(rule)

    async def validate_comprehensive(self, request: ValidationRequest) -> ValidationReport:
        """
        Perform comprehensive validation using all available validators.

        Args:
            request: Validation request with data and options

        Returns:
            Comprehensive validation report
        """
        start_time = datetime.utcnow()

        # Convert data to DataFrame if needed
        if isinstance(request.data, pd.DataFrame):
            data = request.data
        else:
            # Handle other data formats (dict, list, etc.)
            data = pd.DataFrame(request.data)

        # Initialize report
        report = ValidationReport(
            dataset_name=request.options.get('dataset_name', 'unknown'),
            overall_valid=True,
            schema_validation=None,
            rule_validation=None,
            profiling_results=None
        )

        # Create validation context
        context = ValidationContext(**(request.context or {}))

        # Perform requested validations
        if "schema" in request.validation_types:
            report.schema_validation = await self._validate_schema(data, request.schema_id, context)
            report.validation_performance["schema"] = report.schema_validation.execution_time_ms or 0

        if "rules" in request.validation_types:
            report.rule_validation = await self._validate_business_rules(data, request.rule_categories, context)
            report.validation_performance["rules"] = report.rule_validation.execution_time_ms or 0

        if "profile" in request.validation_types:
            report.profiling_results = await self._profile_data(data, context)
            report.validation_performance["profile"] = report.profiling_results.execution_time_ms or 0

        # Calculate overall metrics
        await self._calculate_overall_metrics(report)

        # Generate consolidated recommendations
        await self._generate_consolidated_recommendations(report)

        # Calculate total execution time
        end_time = datetime.utcnow()
        report.total_execution_time_ms = (end_time - start_time).total_seconds() * 1000

        # Store in history
        self.validation_history.append(report)

        return report

    async def _validate_schema(self, data: pd.DataFrame, schema_id: Optional[str],
                             context: ValidationContext) -> SchemaValidationResult:
        """Perform schema validation."""
        schema = None
        if schema_id:
            schema = self.schema_tracker.get_schema(schema_id)

        return await self.schema_validator.validate(data, schema)

    async def _validate_business_rules(self, data: pd.DataFrame, rule_categories: Optional[List[str]],
                                     context: ValidationContext) -> RuleValidationResult:
        """Perform business rule validation."""
        # Filter rules by category if specified
        if rule_categories:
            # Temporarily disable rules not in specified categories
            original_rules = dict(self.business_rule_engine.rules)
            filtered_rules = {}

            for rule_id, rule in original_rules.items():
                if rule.category in rule_categories:
                    filtered_rules[rule_id] = rule

            self.business_rule_engine.rules = filtered_rules

            try:
                result = await self.business_rule_engine.validate(data)
            finally:
                # Restore original rules
                self.business_rule_engine.rules = original_rules

            return result
        else:
            return await self.business_rule_engine.validate(data)

    async def _profile_data(self, data: pd.DataFrame, context: ValidationContext) -> ProfileResult:
        """Perform data profiling."""
        return await self.data_profiler.validate(data, dataset_name=context.data_source or "unknown")

    async def _calculate_overall_metrics(self, report: ValidationReport):
        """Calculate overall validation metrics."""
        all_issues = []

        # Collect all issues
        if report.schema_validation:
            all_issues.extend(report.schema_validation.issues)

        if report.rule_validation:
            all_issues.extend(report.rule_validation.issues)

        if report.profiling_results:
            all_issues.extend(report.profiling_results.issues)

        # Count issues by severity
        severity_counts = {severity.value: 0 for severity in ValidationSeverity}
        for issue in all_issues:
            severity_counts[issue.severity.value] += 1

        report.total_issues = len(all_issues)
        report.severity_summary = severity_counts

        # Determine overall validity
        critical_errors = severity_counts.get(ValidationSeverity.CRITICAL.value, 0)
        errors = severity_counts.get(ValidationSeverity.ERROR.value, 0)
        report.overall_valid = (critical_errors == 0 and errors == 0)

        # Calculate data quality score (0-100)
        report.data_quality_score = await self._calculate_quality_score(report)

    async def _calculate_quality_score(self, report: ValidationReport) -> float:
        """Calculate overall data quality score."""
        score = 100.0

        # Deduct points for issues by severity
        if report.severity_summary:
            critical_penalty = report.severity_summary.get(ValidationSeverity.CRITICAL.value, 0) * 25
            error_penalty = report.severity_summary.get(ValidationSeverity.ERROR.value, 0) * 15
            warning_penalty = report.severity_summary.get(ValidationSeverity.WARNING.value, 0) * 5
            info_penalty = report.severity_summary.get(ValidationSeverity.INFO.value, 0) * 1

            total_penalty = critical_penalty + error_penalty + warning_penalty + info_penalty
            score = max(0.0, score - total_penalty)

        # Boost score based on profiling results
        if report.profiling_results and report.profiling_results.dataset_profile:
            profile = report.profiling_results.dataset_profile

            # Factor in completeness, consistency, and uniqueness
            completeness_boost = (profile.completeness / 100) * 10
            consistency_boost = (profile.consistency / 100) * 10

            score = min(100.0, score + (completeness_boost + consistency_boost) / 2)

        return round(score, 2)

    async def _generate_consolidated_recommendations(self, report: ValidationReport):
        """Generate consolidated recommendations from all validation results."""
        recommendations = set()

        # Schema validation recommendations
        if report.schema_validation and report.schema_validation.suggested_migrations:
            recommendations.update(report.schema_validation.suggested_migrations)

        # Business rule recommendations
        if report.rule_validation:
            for issue in report.rule_validation.issues:
                if issue.suggested_fix:
                    recommendations.add(issue.suggested_fix)

        # Profiling recommendations
        if report.profiling_results and report.profiling_results.dataset_profile:
            recommendations.update(report.profiling_results.dataset_profile.recommendations)

        # Add general recommendations based on quality score
        if report.data_quality_score < 50:
            recommendations.add("Data quality is critically low. Comprehensive data cleaning is required.")
        elif report.data_quality_score < 70:
            recommendations.add("Data quality needs improvement. Focus on addressing critical and error-level issues.")
        elif report.data_quality_score < 90:
            recommendations.add("Data quality is good but can be improved by addressing remaining warnings.")

        report.recommendations = list(recommendations)

    # Schema Management Methods

    def register_schema(self, schema: Schema) -> None:
        """Register a new schema version."""
        self.schema_tracker.register_schema(schema)

    def get_schema(self, name: str, version: Optional[str] = None) -> Optional[Schema]:
        """Get a schema by name and version."""
        return self.schema_tracker.get_schema(name, version)

    def compare_schemas(self, old_schema: Schema, new_schema: Schema) -> List[Dict[str, Any]]:
        """Compare two schemas and get changes."""
        changes = self.schema_tracker.compare_schemas(old_schema, new_schema)
        return [change.dict() for change in changes]

    def check_schema_compatibility(self, old_schema: Schema, new_schema: Schema) -> Dict[str, Any]:
        """Check compatibility between schemas."""
        compatibility, issues = self.compatibility_checker.check_compatibility(old_schema, new_schema)
        return {
            "compatibility_level": compatibility.value,
            "issues": issues
        }

    # Business Rule Management Methods

    def add_business_rule(self, rule: BusinessRule) -> None:
        """Add a business rule."""
        self.business_rule_engine.add_rule(rule)

    def remove_business_rule(self, rule_id: str) -> bool:
        """Remove a business rule."""
        return self.business_rule_engine.remove_rule(rule_id)

    def get_business_rule(self, rule_id: str) -> Optional[BusinessRule]:
        """Get a business rule by ID."""
        return self.business_rule_engine.get_rule(rule_id)

    def get_rules_by_category(self, category: str) -> List[BusinessRule]:
        """Get all rules in a category."""
        return self.business_rule_engine.get_rules_by_category(category)

    def get_available_industry_templates(self) -> List[str]:
        """Get list of available industry templates."""
        return ["financial", "healthcare", "retail"]

    def apply_industry_template(self, industry: str) -> bool:
        """Apply an industry-specific rule template."""
        if industry == "financial":
            template = IndustryTemplates.get_financial_template()
        elif industry == "healthcare":
            template = IndustryTemplates.get_healthcare_template()
        elif industry == "retail":
            template = IndustryTemplates.get_retail_template()
        else:
            return False

        for rule in template.rules:
            self.business_rule_engine.add_rule(rule)

        return True

    # Validation History and Analytics

    def get_validation_history(self, limit: Optional[int] = None) -> List[ValidationReport]:
        """Get validation history."""
        if limit:
            return self.validation_history[-limit:]
        return self.validation_history

    def get_validation_analytics(self) -> Dict[str, Any]:
        """Get analytics from validation history."""
        if not self.validation_history:
            return {}

        total_validations = len(self.validation_history)
        successful_validations = len([r for r in self.validation_history if r.overall_valid])

        avg_quality_score = sum(r.data_quality_score for r in self.validation_history) / total_validations
        avg_execution_time = sum(r.total_execution_time_ms for r in self.validation_history) / total_validations

        # Most common issues
        all_issues = []
        for report in self.validation_history:
            if report.schema_validation:
                all_issues.extend(report.schema_validation.issues)
            if report.rule_validation:
                all_issues.extend(report.rule_validation.issues)
            if report.profiling_results:
                all_issues.extend(report.profiling_results.issues)

        issue_types = {}
        for issue in all_issues:
            issue_type = getattr(issue, 'metadata', {}).get('rule_name', 'Unknown')
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        common_issues = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_validations": total_validations,
            "success_rate": (successful_validations / total_validations) * 100,
            "average_quality_score": round(avg_quality_score, 2),
            "average_execution_time_ms": round(avg_execution_time, 2),
            "most_common_issues": common_issues,
            "validation_trends": self._calculate_validation_trends()
        }

    def _calculate_validation_trends(self) -> Dict[str, Any]:
        """Calculate validation trends over time."""
        if len(self.validation_history) < 2:
            return {}

        recent_reports = self.validation_history[-10:]  # Last 10 validations
        older_reports = self.validation_history[-20:-10] if len(self.validation_history) >= 20 else []

        if not older_reports:
            return {"trend": "insufficient_data"}

        recent_avg_score = sum(r.data_quality_score for r in recent_reports) / len(recent_reports)
        older_avg_score = sum(r.data_quality_score for r in older_reports) / len(older_reports)

        score_trend = recent_avg_score - older_avg_score

        return {
            "quality_score_trend": round(score_trend, 2),
            "trend_direction": "improving" if score_trend > 0 else "declining" if score_trend < 0 else "stable",
            "recent_average": round(recent_avg_score, 2),
            "previous_average": round(older_avg_score, 2)
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the validation service."""
        return {
            "name": "ValidationService",
            "version": "1.0.0",
            "description": "Unified validation service with schema, rule, and profiling capabilities",
            "components": {
                "schema_validator": self.schema_validator.get_validator_info(),
                "business_rule_engine": self.business_rule_engine.get_validator_info(),
                "data_profiler": self.data_profiler.get_validator_info()
            },
            "registered_schemas": len(self.schema_tracker.schemas),
            "active_rules": len([r for r in self.business_rule_engine.rules.values() if r.active]),
            "validation_history_count": len(self.validation_history),
            "supported_industry_templates": self.get_available_industry_templates()
        }
