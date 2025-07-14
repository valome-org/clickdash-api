"""
Metadata validation system.

This module provides comprehensive metadata validation including:
- Metadata completeness checking
- Consistency validation across related data
- Metadata quality scoring
- Automated metadata suggestions
- Cross-reference validation
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import pandas as pd
import re
import uuid

from .base import MetadataInterface, MetadataType, MetadataStatus, MetadataLineage, MetadataContext
from .extractor import DatasetMetadata, ColumnMetadata, ColumnPurpose
from .enhanced import UserEnhancedMetadata, BusinessMeaning, SensitivityMarking


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssueType(str, Enum):
    """Types of validation issues."""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    BUSINESS_LOGIC = "business_logic"
    DATA_QUALITY = "data_quality"
    SCHEMA_VIOLATION = "schema_violation"
    RELATIONSHIP_ERROR = "relationship_error"
    PRIVACY_VIOLATION = "privacy_violation"


class MetadataValidationIssue(BaseModel):
    """Individual metadata validation issue."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issue_type: ValidationIssueType = Field(..., description="Type of validation issue")
    severity: ValidationSeverity = Field(..., description="Issue severity")
    element_id: str = Field(..., description="Element with the issue")
    element_type: MetadataType = Field(..., description="Type of element")
    field_name: Optional[str] = None

    # Issue details
    message: str = Field(..., description="Human-readable issue description")
    current_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    suggested_fix: Optional[str] = None

    # Context
    related_elements: List[str] = Field(default_factory=list, description="Related elements")
    business_impact: Optional[str] = None

    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    rule_id: Optional[str] = None
    auto_fixable: bool = Field(default=False, description="Whether issue can be auto-fixed")


class MetadataValidationResult(BaseModel):
    """Result of metadata validation operation."""

    element_id: str = Field(..., description="Validated element ID")
    element_type: MetadataType = Field(..., description="Element type")
    overall_score: float = Field(default=0.0, description="Overall validation score (0-1)")

    # Issue breakdown
    issues: List[MetadataValidationIssue] = Field(default_factory=list)
    critical_count: int = Field(default=0)
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    info_count: int = Field(default=0)

    # Quality scores
    completeness_score: float = Field(default=0.0, description="Completeness score (0-1)")
    consistency_score: float = Field(default=0.0, description="Consistency score (0-1)")
    accuracy_score: float = Field(default=0.0, description="Accuracy score (0-1)")
    business_value_score: float = Field(default=0.0, description="Business value score (0-1)")

    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    auto_fix_suggestions: List[str] = Field(default_factory=list, description="Auto-fixable issues")

    # Validation metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validation_version: str = Field(default="1.0")
    validator_id: Optional[str] = None


class ValidationRule(BaseModel):
    """Definition of a metadata validation rule."""

    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: ValidationIssueType = Field(..., description="Rule category")
    severity: ValidationSeverity = Field(..., description="Default severity")

    # Rule conditions
    applicable_types: List[MetadataType] = Field(..., description="Applicable metadata types")
    required_fields: List[str] = Field(default_factory=list, description="Required fields")
    field_patterns: Dict[str, str] = Field(default_factory=dict, description="Field pattern requirements")
    business_rules: List[str] = Field(default_factory=list, description="Business logic rules")

    # Rule behavior
    auto_fixable: bool = Field(default=False, description="Whether violations can be auto-fixed")
    enabled: bool = Field(default=True, description="Whether rule is active")
    priority: int = Field(default=100, description="Rule priority (lower = higher priority)")

    # Rule metadata
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")


class MetadataConsistencyChecker:
    """Checks consistency across related metadata elements."""

    def __init__(self):
        self.consistency_rules = self._load_consistency_rules()

    def check_consistency(self, metadata_set: List[Union[DatasetMetadata, UserEnhancedMetadata]]) -> List[MetadataValidationIssue]:
        """Check consistency across multiple metadata elements."""
        issues = []

        # Group metadata by type
        dataset_metadata = [m for m in metadata_set if isinstance(m, DatasetMetadata)]
        enhanced_metadata = [m for m in metadata_set if isinstance(m, UserEnhancedMetadata)]

        # Check dataset-level consistency
        for dataset in dataset_metadata:
            issues.extend(self._check_dataset_consistency(dataset))

        # Check cross-element consistency
        issues.extend(self._check_cross_element_consistency(metadata_set))

        # Check relationship consistency
        issues.extend(self._check_relationship_consistency(metadata_set))

        return issues

    def _check_dataset_consistency(self, dataset: DatasetMetadata) -> List[MetadataValidationIssue]:
        """Check consistency within a single dataset."""
        issues = []

        # Check column count consistency
        if len(dataset.columns) != dataset.total_columns:
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                element_id=dataset.dataset_id,
                element_type=MetadataType.DATASET,
                message=f"Column count mismatch: metadata has {len(dataset.columns)} columns but total_columns is {dataset.total_columns}",
                suggested_fix="Update total_columns to match actual column count"
            ))

        # Check primary key consistency
        for pk in dataset.primary_keys:
            if pk not in dataset.columns:
                issues.append(MetadataValidationIssue(
                    issue_type=ValidationIssueType.CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    element_id=dataset.dataset_id,
                    element_type=MetadataType.DATASET,
                    field_name="primary_keys",
                    message=f"Primary key '{pk}' not found in columns",
                    suggested_fix=f"Remove '{pk}' from primary_keys or add corresponding column metadata"
                ))

        # Check foreign key consistency
        for fk_column, ref_column in dataset.foreign_keys.items():
            if fk_column not in dataset.columns:
                issues.append(MetadataValidationIssue(
                    issue_type=ValidationIssueType.CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    element_id=dataset.dataset_id,
                    element_type=MetadataType.DATASET,
                    field_name="foreign_keys",
                    message=f"Foreign key column '{fk_column}' not found in columns",
                    suggested_fix=f"Remove '{fk_column}' from foreign_keys or add corresponding column metadata"
                ))

        # Check quality score consistency
        if dataset.columns:
            avg_column_quality = sum(col.quality_score for col in dataset.columns.values()) / len(dataset.columns)
            if abs(dataset.quality_score - avg_column_quality) > 0.2:
                issues.append(MetadataValidationIssue(
                    issue_type=ValidationIssueType.CONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    element_id=dataset.dataset_id,
                    element_type=MetadataType.DATASET,
                    field_name="quality_score",
                    message=f"Dataset quality score ({dataset.quality_score:.2f}) differs significantly from average column quality ({avg_column_quality:.2f})",
                    suggested_fix="Recalculate dataset quality score based on column scores"
                ))

        return issues

    def _check_cross_element_consistency(self, metadata_set: List[Any]) -> List[MetadataValidationIssue]:
        """Check consistency across different metadata elements."""
        issues = []

        # Build element lookup
        elements_by_id = {getattr(m, 'dataset_id', getattr(m, 'element_id', None)): m for m in metadata_set}

        # Check enhanced metadata references
        for metadata in metadata_set:
            if isinstance(metadata, UserEnhancedMetadata):
                # Check related elements exist
                for related_id in metadata.related_elements:
                    if related_id not in elements_by_id:
                        issues.append(MetadataValidationIssue(
                            issue_type=ValidationIssueType.CONSISTENCY,
                            severity=ValidationSeverity.WARNING,
                            element_id=metadata.element_id,
                            element_type=metadata.element_type,
                            field_name="related_elements",
                            message=f"Related element '{related_id}' not found in metadata set",
                            suggested_fix=f"Remove reference to '{related_id}' or add corresponding metadata"
                        ))

                # Check parent-child relationships
                for parent_id in metadata.parent_elements:
                    if parent_id not in elements_by_id:
                        issues.append(MetadataValidationIssue(
                            issue_type=ValidationIssueType.CONSISTENCY,
                            severity=ValidationSeverity.ERROR,
                            element_id=metadata.element_id,
                            element_type=metadata.element_type,
                            field_name="parent_elements",
                            message=f"Parent element '{parent_id}' not found",
                            suggested_fix=f"Remove reference to '{parent_id}' or add corresponding metadata"
                        ))

        return issues

    def _check_relationship_consistency(self, metadata_set: List[Any]) -> List[MetadataValidationIssue]:
        """Check relationship consistency across elements."""
        issues = []

        # Check bidirectional relationships
        enhanced_elements = [m for m in metadata_set if isinstance(m, UserEnhancedMetadata)]

        for element in enhanced_elements:
            # Check parent-child bidirectionality
            for child_id in element.child_elements:
                child_element = next((e for e in enhanced_elements if e.element_id == child_id), None)
                if child_element and element.element_id not in child_element.parent_elements:
                    issues.append(MetadataValidationIssue(
                        issue_type=ValidationIssueType.RELATIONSHIP_ERROR,
                        severity=ValidationSeverity.WARNING,
                        element_id=element.element_id,
                        element_type=element.element_type,
                        message=f"Child element '{child_id}' does not reference this element as parent",
                        related_elements=[child_id],
                        suggested_fix="Add bidirectional parent-child reference",
                        auto_fixable=True
                    ))

        return issues

    def _load_consistency_rules(self) -> List[ValidationRule]:
        """Load predefined consistency rules."""
        return [
            ValidationRule(
                name="Column Count Consistency",
                description="Dataset column count should match actual columns",
                category=ValidationIssueType.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                applicable_types=[MetadataType.DATASET]
            ),
            ValidationRule(
                name="Primary Key Existence",
                description="Primary keys should exist in column list",
                category=ValidationIssueType.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                applicable_types=[MetadataType.DATASET]
            ),
            ValidationRule(
                name="Bidirectional Relationships",
                description="Parent-child relationships should be bidirectional",
                category=ValidationIssueType.RELATIONSHIP_ERROR,
                severity=ValidationSeverity.WARNING,
                applicable_types=[MetadataType.COLUMN, MetadataType.DATASET],
                auto_fixable=True
            )
        ]


class MetadataQualityScorer:
    """Calculates quality scores for metadata elements."""

    def __init__(self):
        self.scoring_weights = {
            'completeness': 0.35,
            'consistency': 0.25,
            'accuracy': 0.25,
            'business_value': 0.15
        }

    def calculate_quality_score(self, metadata: Union[DatasetMetadata, UserEnhancedMetadata, ColumnMetadata]) -> Dict[str, float]:
        """Calculate comprehensive quality scores for metadata."""

        if isinstance(metadata, DatasetMetadata):
            return self._score_dataset_metadata(metadata)
        elif isinstance(metadata, UserEnhancedMetadata):
            return self._score_enhanced_metadata(metadata)
        elif isinstance(metadata, ColumnMetadata):
            return self._score_column_metadata(metadata)
        else:
            return {'overall': 0.0}

    def _score_dataset_metadata(self, metadata: DatasetMetadata) -> Dict[str, float]:
        """Score dataset-level metadata quality."""
        scores = {}

        # Completeness score
        completeness_factors = []
        completeness_factors.append(1.0 if metadata.name else 0.0)
        completeness_factors.append(1.0 if metadata.description else 0.5)
        completeness_factors.append(1.0 if metadata.business_domain else 0.7)
        completeness_factors.append(1.0 if metadata.primary_keys else 0.6)
        completeness_factors.append(1.0 if metadata.columns else 0.0)

        scores['completeness'] = sum(completeness_factors) / len(completeness_factors)

        # Consistency score (based on internal consistency)
        consistency_factors = []
        consistency_factors.append(1.0 if len(metadata.columns) == metadata.total_columns else 0.5)
        consistency_factors.append(1.0 if all(pk in metadata.columns for pk in metadata.primary_keys) else 0.3)
        consistency_factors.append(1.0 if metadata.quality_score >= 0 else 0.0)

        scores['consistency'] = sum(consistency_factors) / len(consistency_factors)

        # Accuracy score (based on data quality metrics)
        accuracy_factors = []
        accuracy_factors.append(metadata.completeness)
        accuracy_factors.append(metadata.quality_score)
        if metadata.columns:
            avg_column_accuracy = sum(col.quality_score for col in metadata.columns.values()) / len(metadata.columns)
            accuracy_factors.append(avg_column_accuracy)

        scores['accuracy'] = sum(accuracy_factors) / len(accuracy_factors)

        # Business value score
        business_factors = []
        business_factors.append(1.0 if metadata.business_domain else 0.0)
        business_factors.append(1.0 if metadata.use_cases else 0.3)
        business_factors.append(1.0 if metadata.stakeholders else 0.5)
        business_factors.append(1.0 if metadata.lineage else 0.7)

        scores['business_value'] = sum(business_factors) / len(business_factors)

        # Overall score
        scores['overall'] = sum(scores[key] * self.scoring_weights[key] for key in self.scoring_weights)

        return scores

    def _score_enhanced_metadata(self, metadata: UserEnhancedMetadata) -> Dict[str, float]:
        """Score user-enhanced metadata quality."""
        scores = {}

        # Completeness score
        completeness_factors = []
        completeness_factors.append(1.0 if metadata.display_name else 0.5)
        completeness_factors.append(1.0 if metadata.description else 0.3)
        completeness_factors.append(1.0 if metadata.business_meaning else 0.2)
        completeness_factors.append(1.0 if metadata.sensitivity_marking else 0.8)
        completeness_factors.append(1.0 if metadata.tags else 0.6)
        completeness_factors.append(1.0 if metadata.categories else 0.7)

        scores['completeness'] = sum(completeness_factors) / len(completeness_factors)

        # Consistency score
        consistency_factors = []
        consistency_factors.append(1.0 if metadata.status != MetadataStatus.UNKNOWN else 0.5)
        consistency_factors.append(1.0 if metadata.version else 0.8)

        # Check business meaning consistency
        if metadata.business_meaning and metadata.description:
            # Simple heuristic: check if description length is reasonable
            consistency_factors.append(1.0 if len(metadata.description) > 20 else 0.6)
        else:
            consistency_factors.append(0.5)

        scores['consistency'] = sum(consistency_factors) / len(consistency_factors)

        # Accuracy score
        accuracy_factors = []
        accuracy_factors.append((metadata.user_quality_rating or 3) / 5.0)  # Default to 3/5 if not rated
        accuracy_factors.append(1.0 if not metadata.improvement_suggestions else 0.8)

        scores['accuracy'] = sum(accuracy_factors) / len(accuracy_factors)

        # Business value score
        business_factors = []
        business_factors.append(1.0 if metadata.business_meaning else 0.0)
        business_factors.append(1.0 if metadata.sensitivity_marking else 0.3)
        business_factors.append(1.0 if metadata.related_elements else 0.5)
        business_factors.append(1.0 if metadata.custom_fields else 0.7)

        scores['business_value'] = sum(business_factors) / len(business_factors)

        # Overall score
        scores['overall'] = sum(scores[key] * self.scoring_weights[key] for key in self.scoring_weights)

        return scores

    def _score_column_metadata(self, metadata: ColumnMetadata) -> Dict[str, float]:
        """Score column-level metadata quality."""
        scores = {}

        # Completeness score
        completeness_factors = []
        completeness_factors.append(1.0 if metadata.column_name else 0.0)
        completeness_factors.append(1.0 if metadata.purpose != ColumnPurpose.UNKNOWN else 0.3)
        completeness_factors.append(1.0 if metadata.business_meaning else 0.5)
        completeness_factors.append(1.0 if metadata.description else 0.6)

        scores['completeness'] = sum(completeness_factors) / len(completeness_factors)

        # Consistency score
        scores['consistency'] = metadata.confidence_score  # Use confidence as consistency proxy

        # Accuracy score
        scores['accuracy'] = metadata.quality_score

        # Business value score
        business_factors = []
        business_factors.append(1.0 if metadata.business_meaning else 0.0)
        business_factors.append(1.0 if metadata.business_domain else 0.5)
        business_factors.append(1.0 if metadata.purpose != ColumnPurpose.UNKNOWN else 0.0)

        scores['business_value'] = sum(business_factors) / len(business_factors)

        # Overall score
        scores['overall'] = sum(scores[key] * self.scoring_weights[key] for key in self.scoring_weights)

        return scores


class MetadataRecommendationEngine:
    """Generates recommendations for improving metadata quality."""

    def __init__(self):
        self.recommendation_templates = self._load_recommendation_templates()

    def generate_recommendations(self, metadata: Any, validation_result: MetadataValidationResult) -> List[str]:
        """Generate specific recommendations for improving metadata."""
        recommendations = []

        # Analyze validation issues
        for issue in validation_result.issues:
            if issue.suggested_fix:
                recommendations.append(issue.suggested_fix)

        # Generate score-based recommendations
        if validation_result.completeness_score < 0.7:
            recommendations.extend(self._get_completeness_recommendations(metadata))

        if validation_result.consistency_score < 0.8:
            recommendations.extend(self._get_consistency_recommendations(metadata))

        if validation_result.business_value_score < 0.6:
            recommendations.extend(self._get_business_value_recommendations(metadata))

        # Remove duplicates while preserving order
        unique_recommendations = []
        seen = set()
        for rec in recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)

        return unique_recommendations[:10]  # Limit to top 10 recommendations

    def _get_completeness_recommendations(self, metadata: Any) -> List[str]:
        """Generate recommendations for improving completeness."""
        recommendations = []

        if isinstance(metadata, DatasetMetadata):
            if not metadata.description:
                recommendations.append("Add a comprehensive description explaining the dataset's purpose and content")
            if not metadata.business_domain:
                recommendations.append("Classify the dataset into an appropriate business domain")
            if not metadata.primary_keys:
                recommendations.append("Identify and specify primary key columns")
            if not metadata.use_cases:
                recommendations.append("Document primary use cases for this dataset")

        elif isinstance(metadata, UserEnhancedMetadata):
            if not metadata.description:
                recommendations.append("Add a detailed description explaining the business purpose")
            if not metadata.business_meaning:
                recommendations.append("Define the business meaning and context")
            if not metadata.tags:
                recommendations.append("Add relevant tags for better discoverability")
            if not metadata.sensitivity_marking:
                recommendations.append("Add privacy classification for proper data handling")

        elif isinstance(metadata, ColumnMetadata):
            if metadata.purpose == ColumnPurpose.UNKNOWN:
                recommendations.append("Identify and classify the column's business purpose")
            if not metadata.business_meaning:
                recommendations.append("Add business meaning to explain the column's role")

        return recommendations

    def _get_consistency_recommendations(self, metadata: Any) -> List[str]:
        """Generate recommendations for improving consistency."""
        recommendations = []

        if isinstance(metadata, DatasetMetadata):
            if len(metadata.columns) != metadata.total_columns:
                recommendations.append("Update column count to match actual number of columns")
            if metadata.quality_score < 0.6:
                recommendations.append("Review and improve data quality scores for individual columns")

        elif isinstance(metadata, UserEnhancedMetadata):
            if metadata.status == MetadataStatus.UNKNOWN:
                recommendations.append("Set appropriate metadata status (draft, validated, approved)")
            if metadata.description and metadata.business_meaning:
                if len(metadata.description) < 20:
                    recommendations.append("Expand description to provide more comprehensive detail")

        return recommendations

    def _get_business_value_recommendations(self, metadata: Any) -> List[str]:
        """Generate recommendations for improving business value."""
        recommendations = []

        if isinstance(metadata, DatasetMetadata):
            if not metadata.stakeholders:
                recommendations.append("Identify and document key stakeholders who use this data")
            if not metadata.lineage:
                recommendations.append("Document data lineage to track data origins and transformations")

        elif isinstance(metadata, UserEnhancedMetadata):
            if not metadata.business_meaning:
                recommendations.append("Add business context to explain how this data creates value")
            if not metadata.related_elements:
                recommendations.append("Map relationships to other relevant data elements")
            if not metadata.custom_fields:
                recommendations.append("Consider adding domain-specific metadata fields")

        return recommendations

    def _load_recommendation_templates(self) -> Dict[str, List[str]]:
        """Load predefined recommendation templates."""
        return {
            'completeness': [
                "Add comprehensive description",
                "Specify business domain",
                "Identify primary keys",
                "Document use cases",
                "Add relevant tags"
            ],
            'consistency': [
                "Align column counts",
                "Review quality scores",
                "Set proper status",
                "Expand descriptions"
            ],
            'business_value': [
                "Identify stakeholders",
                "Document lineage",
                "Add business context",
                "Map relationships",
                "Add custom fields"
            ]
        }


class MetadataValidator(MetadataInterface):
    """Main metadata validation service that coordinates all validation activities."""

    def __init__(self, context: Optional[MetadataContext] = None):
        super().__init__(context)
        self.consistency_checker = MetadataConsistencyChecker()
        self.quality_scorer = MetadataQualityScorer()
        self.recommendation_engine = MetadataRecommendationEngine()
        self.validation_rules: Dict[str, ValidationRule] = {}

    async def validate_metadata(self, metadata: Union[DatasetMetadata, UserEnhancedMetadata, ColumnMetadata]) -> MetadataValidationResult:
        """
        Perform comprehensive validation of metadata.

        Args:
            metadata: Metadata to validate

        Returns:
            MetadataValidationResult with validation details
        """
        try:
            # Determine element details
            if isinstance(metadata, DatasetMetadata):
                element_id = metadata.dataset_id
                element_type = MetadataType.DATASET
            elif isinstance(metadata, UserEnhancedMetadata):
                element_id = metadata.element_id
                element_type = metadata.element_type
            elif isinstance(metadata, ColumnMetadata):
                element_id = metadata.column_name
                element_type = MetadataType.COLUMN
            else:
                raise ValueError(f"Unsupported metadata type: {type(metadata)}")

            # Run validation checks
            issues = await self._run_validation_checks(metadata)

            # Calculate quality scores
            quality_scores = self.quality_scorer.calculate_quality_score(metadata)

            # Count issues by severity
            critical_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.CRITICAL)
            error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
            warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)
            info_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.INFO)

            # Create validation result
            result = MetadataValidationResult(
                element_id=element_id,
                element_type=element_type,
                overall_score=quality_scores.get('overall', 0.0),
                issues=issues,
                critical_count=critical_count,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
                completeness_score=quality_scores.get('completeness', 0.0),
                consistency_score=quality_scores.get('consistency', 0.0),
                accuracy_score=quality_scores.get('accuracy', 0.0),
                business_value_score=quality_scores.get('business_value', 0.0),
                validator_id=self.context.user_id
            )

            # Generate recommendations
            result.recommendations = self.recommendation_engine.generate_recommendations(metadata, result)

            # Identify auto-fixable issues
            result.auto_fix_suggestions = [
                issue.suggested_fix for issue in issues
                if issue.auto_fixable and issue.suggested_fix
            ]

            return result

        except Exception as e:
            # Return error result
            return MetadataValidationResult(
                element_id="unknown",
                element_type=MetadataType.DATASET,
                issues=[MetadataValidationIssue(
                    issue_type=ValidationIssueType.SCHEMA_VIOLATION,
                    severity=ValidationSeverity.CRITICAL,
                    element_id="unknown",
                    element_type=MetadataType.DATASET,
                    message=f"Validation failed: {str(e)}"
                )]
            )

    async def _run_validation_checks(self, metadata: Any) -> List[MetadataValidationIssue]:
        """Run all applicable validation checks on metadata."""
        issues = []

        # Run rule-based validation
        issues.extend(await self._validate_against_rules(metadata))

        # Run type-specific validation
        if isinstance(metadata, DatasetMetadata):
            issues.extend(await self._validate_dataset_metadata(metadata))
        elif isinstance(metadata, UserEnhancedMetadata):
            issues.extend(await self._validate_enhanced_metadata(metadata))
        elif isinstance(metadata, ColumnMetadata):
            issues.extend(await self._validate_column_metadata(metadata))

        return issues

    async def _validate_against_rules(self, metadata: Any) -> List[MetadataValidationIssue]:
        """Validate metadata against defined rules."""
        issues = []

        for rule in self.validation_rules.values():
            if not rule.enabled:
                continue

            # Check if rule applies to this metadata type
            metadata_type = None
            if isinstance(metadata, DatasetMetadata):
                metadata_type = MetadataType.DATASET
            elif isinstance(metadata, UserEnhancedMetadata):
                metadata_type = metadata.element_type
            elif isinstance(metadata, ColumnMetadata):
                metadata_type = MetadataType.COLUMN

            if metadata_type not in rule.applicable_types:
                continue

            # Validate required fields
            for field_name in rule.required_fields:
                if not hasattr(metadata, field_name) or getattr(metadata, field_name) is None:
                    issues.append(MetadataValidationIssue(
                        issue_type=rule.category,
                        severity=rule.severity,
                        element_id=getattr(metadata, 'dataset_id', getattr(metadata, 'element_id', getattr(metadata, 'column_name', 'unknown'))),
                        element_type=metadata_type or MetadataType.DATASET,
                        field_name=field_name,
                        message=f"Required field '{field_name}' is missing",
                        suggested_fix=f"Add value for required field '{field_name}'",
                        rule_id=rule.rule_id,
                        auto_fixable=rule.auto_fixable
                    ))

        return issues

    async def _validate_dataset_metadata(self, metadata: DatasetMetadata) -> List[MetadataValidationIssue]:
        """Validate dataset-specific metadata."""
        issues = []

        # Check for obvious inconsistencies
        if metadata.total_rows < 0:
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.DATA_QUALITY,
                severity=ValidationSeverity.ERROR,
                element_id=metadata.dataset_id,
                element_type=MetadataType.DATASET,
                field_name="total_rows",
                message="Total rows cannot be negative",
                current_value=metadata.total_rows,
                suggested_fix="Set total_rows to actual row count"
            ))

        if metadata.total_columns < 0:
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.DATA_QUALITY,
                severity=ValidationSeverity.ERROR,
                element_id=metadata.dataset_id,
                element_type=MetadataType.DATASET,
                field_name="total_columns",
                message="Total columns cannot be negative",
                current_value=metadata.total_columns,
                suggested_fix="Set total_columns to actual column count"
            ))

        # Check completeness score bounds
        if not (0 <= metadata.completeness <= 1):
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.DATA_QUALITY,
                severity=ValidationSeverity.ERROR,
                element_id=metadata.dataset_id,
                element_type=MetadataType.DATASET,
                field_name="completeness",
                message="Completeness score must be between 0 and 1",
                current_value=metadata.completeness,
                suggested_fix="Recalculate completeness score"
            ))

        return issues

    async def _validate_enhanced_metadata(self, metadata: UserEnhancedMetadata) -> List[MetadataValidationIssue]:
        """Validate user-enhanced metadata."""
        issues = []

        # Check for circular references in relationships
        if metadata.element_id in metadata.related_elements:
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.RELATIONSHIP_ERROR,
                severity=ValidationSeverity.WARNING,
                element_id=metadata.element_id,
                element_type=metadata.element_type,
                field_name="related_elements",
                message="Element cannot be related to itself",
                suggested_fix="Remove self-reference from related_elements",
                auto_fixable=True
            ))

        # Check for logical parent-child inconsistencies
        if set(metadata.parent_elements) & set(metadata.child_elements):
            overlapping = set(metadata.parent_elements) & set(metadata.child_elements)
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.RELATIONSHIP_ERROR,
                severity=ValidationSeverity.ERROR,
                element_id=metadata.element_id,
                element_type=metadata.element_type,
                message=f"Elements cannot be both parent and child: {overlapping}",
                suggested_fix="Remove conflicting parent-child relationships"
            ))

        # Validate custom fields against definitions
        for field_name, field_value in metadata.custom_fields.items():
            # This would check against registered custom field definitions
            # For now, just validate that values are not None if they exist
            if field_value is None:
                issues.append(MetadataValidationIssue(
                    issue_type=ValidationIssueType.COMPLETENESS,
                    severity=ValidationSeverity.INFO,
                    element_id=metadata.element_id,
                    element_type=metadata.element_type,
                    field_name=f"custom_fields.{field_name}",
                    message=f"Custom field '{field_name}' has null value",
                    suggested_fix=f"Provide value for custom field '{field_name}' or remove it"
                ))

        return issues

    async def _validate_column_metadata(self, metadata: ColumnMetadata) -> List[MetadataValidationIssue]:
        """Validate column-specific metadata."""
        issues = []

        # Check confidence score bounds
        if not (0 <= metadata.confidence_score <= 1):
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.DATA_QUALITY,
                severity=ValidationSeverity.WARNING,
                element_id=metadata.column_name,
                element_type=MetadataType.COLUMN,
                field_name="confidence_score",
                message="Confidence score must be between 0 and 1",
                current_value=metadata.confidence_score,
                suggested_fix="Recalculate confidence score"
            ))

        # Check for obviously wrong purpose assignments
        if (metadata.purpose == ColumnPurpose.EMAIL and
            metadata.data_type not in ['string', 'object']):
            issues.append(MetadataValidationIssue(
                issue_type=ValidationIssueType.CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                element_id=metadata.column_name,
                element_type=MetadataType.COLUMN,
                field_name="purpose",
                message="Email columns should typically be string/text type",
                suggested_fix="Review purpose assignment or data type classification"
            ))

        return issues

    async def batch_validate(self, metadata_list: List[Any]) -> List[MetadataValidationResult]:
        """Validate multiple metadata elements and check cross-element consistency."""
        results = []

        # Validate each element individually
        for metadata in metadata_list:
            result = await self.validate_metadata(metadata)
            results.append(result)

        # Check cross-element consistency
        consistency_issues = self.consistency_checker.check_consistency(metadata_list)

        # Add consistency issues to relevant results
        for issue in consistency_issues:
            # Find the result for this element
            matching_result = next((r for r in results if r.element_id == issue.element_id), None)
            if matching_result:
                matching_result.issues.append(issue)
                # Update issue counts
                if issue.severity == ValidationSeverity.CRITICAL:
                    matching_result.critical_count += 1
                elif issue.severity == ValidationSeverity.ERROR:
                    matching_result.error_count += 1
                elif issue.severity == ValidationSeverity.WARNING:
                    matching_result.warning_count += 1
                else:
                    matching_result.info_count += 1

        return results

    async def extract_metadata(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Extract validation-ready metadata from data source."""
        # This would typically work with the extractor to get metadata for validation
        return {}

    def add_validation_rule(self, rule: ValidationRule):
        """Add a custom validation rule."""
        self.validation_rules[rule.rule_id] = rule

    def remove_validation_rule(self, rule_id: str):
        """Remove a validation rule."""
        if rule_id in self.validation_rules:
            del self.validation_rules[rule_id]
