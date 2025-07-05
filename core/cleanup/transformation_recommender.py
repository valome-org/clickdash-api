"""
Data transformation recommender for intelligent data cleanup.

This module provides intelligent transformation recommendations including:
- Data type optimizations
- Column transformations (normalization, encoding)
- Data format standardization
- Performance optimizations
- Business logic transformations
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import re
from dateutil import parser
import logging
import uuid
from pydantic import BaseModel, Field

from .base import CleanupInterface, CleanupResult, CleanupIssue, CleanupSeverity, CleanupContext, CleanupStrategy

logger = logging.getLogger(__name__)


class TransformationType(str, Enum):
    """Types of data transformations."""
    DATA_TYPE_CONVERSION = "data_type_conversion"
    TEXT_STANDARDIZATION = "text_standardization"
    DATE_STANDARDIZATION = "date_standardization"
    NUMERIC_NORMALIZATION = "numeric_normalization"
    CATEGORICAL_ENCODING = "categorical_encoding"
    COLUMN_SPLITTING = "column_splitting"
    COLUMN_MERGING = "column_merging"
    OUTLIER_TRANSFORMATION = "outlier_transformation"
    SCALING = "scaling"
    FEATURE_ENGINEERING = "feature_engineering"


class TransformationPriority(str, Enum):
    """Priority levels for transformations."""
    CRITICAL = "critical"  # Must be done for data to be usable
    HIGH = "high"  # Strongly recommended
    MEDIUM = "medium"  # Good to have
    LOW = "low"  # Nice to have
    OPTIONAL = "optional"  # User preference


class TransformationSuggestion(BaseModel):
    """Represents a suggested data transformation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique suggestion identifier")
    transformation_type: TransformationType = Field(..., description="Type of transformation")
    priority: TransformationPriority = Field(..., description="Priority level")
    target_columns: List[str] = Field(..., description="Columns to be transformed")
    description: str = Field(..., description="Human-readable description")
    rationale: str = Field(..., description="Why this transformation is recommended")

    # Transformation details
    current_state: Dict[str, Any] = Field(..., description="Current state of the data")
    proposed_state: Dict[str, Any] = Field(..., description="Proposed state after transformation")
    transformation_function: str = Field(..., description="Function or method to apply")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for transformation")

    # Impact assessment
    estimated_impact: str = Field(..., description="Expected impact on data quality")
    confidence: float = Field(default=0.0, description="Confidence in the recommendation (0-1)")
    risk_level: str = Field(default="low", description="Risk level of applying transformation")
    reversible: bool = Field(default=True, description="Whether transformation is reversible")

    # Dependencies
    prerequisites: List[str] = Field(default_factory=list, description="Other transformations that should be done first")
    conflicts_with: List[str] = Field(default_factory=list, description="Transformations that conflict with this one")

    # Metadata
    estimated_execution_time: Optional[float] = Field(default=None, description="Estimated execution time in ms")
    memory_requirements: Optional[str] = Field(default=None, description="Estimated memory requirements")


class TransformationResult(CleanupResult):
    """Specialized result for transformation operations."""

    suggestions_generated: int = Field(default=0, description="Number of transformation suggestions generated")
    transformations_applied: int = Field(default=0, description="Number of transformations applied")
    data_quality_improvement: float = Field(default=0.0, description="Improvement in data quality score")
    transformation_summary: Dict[str, int] = Field(default_factory=dict, description="Summary by transformation type")


class TransformationRecommender(CleanupInterface):
    """Intelligent data transformation recommendation system."""

    def __init__(self):
        self.supported_transformations = list(TransformationType)
        self.text_patterns = self._initialize_text_patterns()
        self.date_patterns = self._initialize_date_patterns()

    def _initialize_text_patterns(self) -> Dict[str, str]:
        """Initialize common text patterns for standardization."""
        return {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
            'postal_code': r'^[0-9]{5}(?:-[0-9]{4})?$',
            'currency': r'^\$?[0-9]{1,3}(,[0-9]{3})*(\.[0-9]{2})?$',
            'percentage': r'^[0-9]{1,3}(\.[0-9]{1,2})?%$',
            'ssn': r'^\d{3}-?\d{2}-?\d{4}$',
            'credit_card': r'^[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}$'
        }

    def _initialize_date_patterns(self) -> List[str]:
        """Initialize common date patterns."""
        return [
            '%Y-%m-%d',  # 2023-01-15
            '%m/%d/%Y',  # 01/15/2023
            '%d/%m/%Y',  # 15/01/2023
            '%Y/%m/%d',  # 2023/01/15
            '%b %d, %Y',  # Jan 15, 2023
            '%B %d, %Y',  # January 15, 2023
            '%d-%b-%Y',  # 15-Jan-2023
            '%Y%m%d',    # 20230115
        ]

    async def clean(self, data: pd.DataFrame, context: Optional[CleanupContext] = None, **kwargs) -> TransformationResult:
        """
        Generate and optionally apply transformation recommendations.

        Args:
            data: DataFrame to analyze and transform
            context: Cleanup context with preferences
            **kwargs: Additional parameters (apply_transformations, transformation_types)

        Returns:
            TransformationResult with suggestions and transformed data
        """
        start_time = datetime.utcnow()

        # Validate input
        try:
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Input must be a pandas DataFrame")

            if hasattr(data, 'empty') and data.empty:
                logger.warning("Input DataFrame is empty")
                return TransformationResult(
                    is_successful=True,
                    cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                    cleaned_data=data.copy(),
                    rollback_info={}
                )

            if not self.validate_input(data):
                return TransformationResult(
                    is_successful=False,
                    cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                    cleaned_data=data.copy(),
                    rollback_info={}
                )

        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return TransformationResult(
                is_successful=False,
                cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                cleaned_data=data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(),
                rollback_info={}
            )

        # Extract parameters
        apply_transformations = kwargs.get('apply_transformations', False)
        transformation_types = kwargs.get('transformation_types', None)

        # Use context strategy if provided
        if context and context.cleanup_strategy:
            if context.cleanup_strategy == CleanupStrategy.AUTOMATIC:
                apply_transformations = True

        result = TransformationResult(
            is_successful=True,
            cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
            cleaned_data=data.copy(),
            rollback_info={}
        )

        try:
            # Generate transformation suggestions
            suggestions = await self._generate_transformation_suggestions(data, transformation_types, context)
            result.suggestions_generated = len(suggestions)

            # Create cleanup issues from suggestions
            issues = await self._create_transformation_issues(suggestions)
            result.issues_found = issues

            # Apply transformations if requested
            if apply_transformations and suggestions:
                transformed_data, applied_count, summary = await self._apply_transformations(
                    data, suggestions, context
                )
                result.cleaned_data = transformed_data
                result.transformations_applied = applied_count
                result.transformation_summary = summary

                # Mark issues as resolved for applied transformations
                for i, issue in enumerate(issues[:applied_count]):
                    result.mark_issue_resolved(issue.id)

            # Calculate execution time
            end_time = datetime.utcnow()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Generate additional recommendations
            result.additional_recommendations = await self._generate_additional_recommendations(
                data, suggestions
            )

        except Exception as e:
            logger.error(f"Transformation recommendation failed: {str(e)}")
            result.is_successful = False
            result.add_issue(CleanupIssue(
                issue_type="transformation_error",
                severity=CleanupSeverity.CRITICAL,
                message=f"Transformation analysis failed: {str(e)}",
                field="",
                suggested_action="Review data format and try again",
                confidence=1.0,
                estimated_impact="No transformation recommendations available"
            ))

        return result

    async def analyze_data(self, data: pd.DataFrame, context: Optional[CleanupContext] = None) -> List[CleanupIssue]:
        """Analyze data to generate transformation suggestions without applying them."""
        suggestions = await self._generate_transformation_suggestions(data, None, context)
        issues = await self._create_transformation_issues(suggestions)
        return issues

    async def _generate_transformation_suggestions(self, data: pd.DataFrame,
                                                 transformation_types: Optional[List[str]],
                                                 context: Optional[CleanupContext]) -> List[TransformationSuggestion]:
        """Generate comprehensive transformation suggestions."""
        suggestions = []

        # Analyze each column
        for column in data.columns:
            column_suggestions = await self._analyze_column_transformations(data, column, context)
            suggestions.extend(column_suggestions)

        # Analyze cross-column transformations
        cross_column_suggestions = await self._analyze_cross_column_transformations(data, context)
        suggestions.extend(cross_column_suggestions)

        # Filter by requested transformation types
        if transformation_types:
            suggestions = [s for s in suggestions if s.transformation_type.value in transformation_types]

        # Prioritize and sort suggestions
        suggestions = self._prioritize_suggestions(suggestions, context)

        return suggestions

    async def _analyze_column_transformations(self, data: pd.DataFrame, column: str,
                                            context: Optional[CleanupContext]) -> List[TransformationSuggestion]:
        """Analyze transformation opportunities for a single column."""
        suggestions = []
        series = data[column]

        # Data type conversion suggestions
        dtype_suggestions = await self._suggest_data_type_conversions(series, column)
        suggestions.extend(dtype_suggestions)

        # Text standardization suggestions
        if pd.api.types.is_string_dtype(series):
            text_suggestions = await self._suggest_text_standardizations(series, column)
            suggestions.extend(text_suggestions)

        # Date standardization suggestions
        date_suggestions = await self._suggest_date_standardizations(series, column)
        suggestions.extend(date_suggestions)

        # Numeric transformation suggestions
        if pd.api.types.is_numeric_dtype(series):
            numeric_suggestions = await self._suggest_numeric_transformations(series, column)
            suggestions.extend(numeric_suggestions)

        # Categorical encoding suggestions
        categorical_suggestions = await self._suggest_categorical_encodings(series, column)
        suggestions.extend(categorical_suggestions)

        return suggestions

    async def _suggest_data_type_conversions(self, series: pd.Series, column: str) -> List[TransformationSuggestion]:
        """Suggest data type conversions for better efficiency and accuracy."""
        suggestions = []
        current_dtype = str(series.dtype)

        # Check if string column can be converted to numeric
        if pd.api.types.is_string_dtype(series):
            numeric_convertible = self._can_convert_to_numeric(series)
            if numeric_convertible:
                suggested_type = "int64" if numeric_convertible == "integer" else "float64"
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.DATA_TYPE_CONVERSION,
                    priority=TransformationPriority.HIGH,
                    target_columns=[column],
                    description=f"Convert column '{column}' from string to {suggested_type}",
                    rationale=f"Column contains numeric data stored as text, conversion will improve performance and enable numeric operations",
                    current_state={"dtype": current_dtype, "sample_values": series.dropna().head(3).tolist()},
                    proposed_state={"dtype": suggested_type},
                    transformation_function="pd.to_numeric",
                    parameters={"errors": "coerce"},
                    estimated_impact="Improved performance and numeric operations",
                    confidence=0.9,
                    risk_level="low",
                    reversible=True,
                    estimated_execution_time=None,
                    memory_requirements=None
                ))

        # Check if string column can be converted to datetime
        if pd.api.types.is_string_dtype(series):
            datetime_convertible = self._can_convert_to_datetime(series)
            if datetime_convertible:
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.DATA_TYPE_CONVERSION,
                    priority=TransformationPriority.HIGH,
                    target_columns=[column],
                    description=f"Convert column '{column}' from string to datetime",
                    rationale="Column contains date/time data that should be properly typed for temporal operations",
                    current_state={"dtype": current_dtype, "sample_values": series.dropna().head(3).tolist()},
                    proposed_state={"dtype": "datetime64[ns]"},
                    transformation_function="pd.to_datetime",
                    parameters={"errors": "coerce", "infer_datetime_format": True},
                    estimated_impact="Enable temporal operations and improved data analysis",
                    confidence=0.85,
                    risk_level="low",
                    reversible=True,
                    estimated_execution_time=None,
                    memory_requirements=None
                ))

        # Check if object column can be converted to category
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            unique_ratio = series.nunique() / len(series) if len(series) > 0 else 0
            if unique_ratio < 0.5 and series.nunique() < 100:  # Low cardinality
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.DATA_TYPE_CONVERSION,
                    priority=TransformationPriority.MEDIUM,
                    target_columns=[column],
                    description=f"Convert column '{column}' to categorical type",
                    rationale=f"Column has low cardinality ({series.nunique()} unique values), categorical type will save memory",
                    current_state={"dtype": current_dtype, "unique_values": series.nunique()},
                    proposed_state={"dtype": "category"},
                    transformation_function="astype",
                    parameters={"dtype": "category"},
                    estimated_impact="Reduced memory usage and potential performance improvement",
                    confidence=0.8,
                    risk_level="low",
                    reversible=True,
                    estimated_execution_time=None,
                    memory_requirements=None
                ))

        return suggestions

    async def _suggest_text_standardizations(self, series: pd.Series, column: str) -> List[TransformationSuggestion]:
        """Suggest text standardization transformations."""
        suggestions = []

        # Check for case inconsistencies
        if self._has_case_inconsistencies(series):
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.TEXT_STANDARDIZATION,
                priority=TransformationPriority.MEDIUM,
                target_columns=[column],
                description=f"Standardize case in column '{column}'",
                rationale="Column has inconsistent case formatting which may affect data analysis",
                current_state={"sample_values": series.dropna().head(5).tolist()},
                proposed_state={"case": "lower"},
                transformation_function="str.lower",
                parameters={},
                estimated_impact="Improved data consistency and matching",
                confidence=0.9,
                risk_level="low",
                reversible=True
            ))

        # Check for whitespace issues
        if self._has_whitespace_issues(series):
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.TEXT_STANDARDIZATION,
                priority=TransformationPriority.HIGH,
                target_columns=[column],
                description=f"Remove extra whitespace from column '{column}'",
                rationale="Column contains leading/trailing whitespace or multiple spaces",
                current_state={"has_whitespace": True},
                proposed_state={"has_whitespace": False},
                transformation_function="str.strip",
                parameters={},
                estimated_impact="Cleaner data and improved matching",
                confidence=0.95,
                risk_level="low",
                reversible=False
            ))

        # Check for pattern-based standardization opportunities
        pattern_suggestions = self._suggest_pattern_standardizations(series, column)
        suggestions.extend(pattern_suggestions)

        return suggestions

    async def _suggest_date_standardizations(self, series: pd.Series, column: str) -> List[TransformationSuggestion]:
        """Suggest date standardization transformations."""
        suggestions = []

        # Check if column contains date-like strings
        if pd.api.types.is_string_dtype(series):
            date_formats = self._detect_date_formats(series)
            if date_formats and len(date_formats) > 1:  # Multiple formats detected
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.DATE_STANDARDIZATION,
                    priority=TransformationPriority.HIGH,
                    target_columns=[column],
                    description=f"Standardize date formats in column '{column}'",
                    rationale=f"Column contains dates in {len(date_formats)} different formats",
                    current_state={"formats": date_formats},
                    proposed_state={"format": "YYYY-MM-DD"},
                    transformation_function="standardize_dates",
                    parameters={"target_format": "%Y-%m-%d"},
                    estimated_impact="Consistent date formatting for analysis",
                    confidence=0.85,
                    risk_level="medium",
                    reversible=True
                ))

        return suggestions

    async def _suggest_numeric_transformations(self, series: pd.Series, column: str) -> List[TransformationSuggestion]:
        """Suggest numeric transformations."""
        suggestions = []

        # Check for scaling needs
        if self._needs_scaling(series):
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.SCALING,
                priority=TransformationPriority.MEDIUM,
                target_columns=[column],
                description=f"Scale values in column '{column}'",
                rationale="Column has values with large magnitude differences, scaling may improve analysis",
                current_state={"min": float(series.min()), "max": float(series.max()), "std": float(series.std())},
                proposed_state={"scaled": True},
                transformation_function="StandardScaler",
                parameters={"method": "standard"},
                estimated_impact="Improved performance in ML algorithms",
                confidence=0.7,
                risk_level="low",
                reversible=True
            ))

        # Check for outlier transformation needs
        outlier_ratio = self._calculate_outlier_ratio(series)
        if outlier_ratio > 0.05:  # More than 5% outliers
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.OUTLIER_TRANSFORMATION,
                priority=TransformationPriority.MEDIUM,
                target_columns=[column],
                description=f"Apply log transformation to column '{column}' to reduce outlier impact",
                rationale=f"Column has {outlier_ratio:.1%} outliers, log transformation may improve distribution",
                current_state={"outlier_ratio": outlier_ratio},
                proposed_state={"transformed": True},
                transformation_function="np.log1p",
                parameters={},
                estimated_impact="Reduced outlier impact and improved distribution",
                confidence=0.6,
                risk_level="medium",
                reversible=True
            ))

        return suggestions

    async def _suggest_categorical_encodings(self, series: pd.Series, column: str) -> List[TransformationSuggestion]:
        """Suggest categorical encoding transformations."""
        suggestions = []

        if pd.api.types.is_string_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
            unique_count = series.nunique()

            # High cardinality categorical variables
            if unique_count > 50:
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.CATEGORICAL_ENCODING,
                    priority=TransformationPriority.LOW,
                    target_columns=[column],
                    description=f"Consider target encoding for high-cardinality column '{column}'",
                    rationale=f"Column has {unique_count} unique categories, may benefit from advanced encoding",
                    current_state={"unique_count": unique_count, "encoding": "none"},
                    proposed_state={"encoding": "target_encoding"},
                    transformation_function="target_encode",
                    parameters={},
                    estimated_impact="Reduced dimensionality while preserving information",
                    confidence=0.5,
                    risk_level="medium",
                    reversible=False
                ))

        return suggestions

    async def _analyze_cross_column_transformations(self, data: pd.DataFrame,
                                                  context: Optional[CleanupContext]) -> List[TransformationSuggestion]:
        """Analyze transformation opportunities across multiple columns."""
        suggestions = []

        # Check for columns that should be merged
        merge_suggestions = self._suggest_column_merges(data)
        suggestions.extend(merge_suggestions)

        # Check for columns that should be split
        split_suggestions = self._suggest_column_splits(data)
        suggestions.extend(split_suggestions)

        return suggestions

    def _can_convert_to_numeric(self, series: pd.Series) -> Optional[str]:
        """Check if string series can be converted to numeric."""
        try:
            non_null_series = series.dropna()
            if len(non_null_series) == 0:
                return None

            # Try converting to numeric
            converted = pd.to_numeric(non_null_series, errors='coerce')
            success_rate = converted.notna().sum() / len(non_null_series)

            if success_rate > 0.9:  # 90% success rate
                # Check if all converted values are integers
                try:
                    if converted.dropna().apply(lambda x: float(x).is_integer()).all():
                        return "integer"
                    else:
                        return "float"
                except (ValueError, TypeError, AttributeError):
                    return "float"

        except Exception as e:
            logger.warning(f"Error checking numeric conversion: {str(e)}")

        return None

    def _can_convert_to_datetime(self, series: pd.Series) -> bool:
        """Check if string series can be converted to datetime."""
        try:
            non_null_series = series.dropna()
            if len(non_null_series) == 0:
                return False

            # Sample a few values to test
            sample_size = min(10, len(non_null_series))
            sample = non_null_series.sample(sample_size) if len(non_null_series) >= sample_size else non_null_series

            success_count = 0
            for value in sample:
                try:
                    # Try both dateutil parser and pandas to_datetime
                    parser.parse(str(value))
                    success_count += 1
                except (ValueError, TypeError, parser.ParserError):
                    # Try pandas to_datetime as fallback
                    try:
                        pd.to_datetime(str(value), errors='raise')
                        success_count += 1
                    except (ValueError, TypeError):
                        pass

            return success_count / len(sample) > 0.8  # 80% success rate

        except Exception as e:
            logger.warning(f"Error checking datetime conversion: {str(e)}")
            return False

    def _has_case_inconsistencies(self, series: pd.Series) -> bool:
        """Check if series has case inconsistencies."""
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return False

        # Check if we have both upper and lower case versions of the same text
        text_counts = {}
        for value in non_null_series:
            normalized = str(value).lower().strip()
            if normalized not in text_counts:
                text_counts[normalized] = set()
            text_counts[normalized].add(str(value))

        # If any normalized text has multiple case variations
        return any(len(variations) > 1 for variations in text_counts.values())

    def _has_whitespace_issues(self, series: pd.Series) -> bool:
        """Check if series has whitespace issues."""
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return False

        # Check for leading/trailing whitespace or multiple spaces
        for value in non_null_series.head(20):  # Sample first 20
            str_value = str(value)
            if str_value != str_value.strip() or '  ' in str_value:
                return True

        return False

    def _suggest_pattern_standardizations(self, series: pd.Series, column: str) -> List[TransformationSuggestion]:
        """Suggest standardizations based on detected patterns."""
        suggestions = []

        for pattern_name, pattern_regex in self.text_patterns.items():
            matches = series.astype(str).str.match(pattern_regex, na=False).sum()
            match_ratio = matches / len(series) if len(series) > 0 else 0

            if match_ratio > 0.7:  # 70% of values match the pattern
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.TEXT_STANDARDIZATION,
                    priority=TransformationPriority.MEDIUM,
                    target_columns=[column],
                    description=f"Standardize {pattern_name} format in column '{column}'",
                    rationale=f"Column appears to contain {pattern_name} data with {match_ratio:.1%} pattern match",
                    current_state={"pattern": pattern_name, "match_ratio": match_ratio},
                    proposed_state={"standardized": True},
                    transformation_function=f"standardize_{pattern_name}",
                    parameters={"pattern": pattern_regex},
                    estimated_impact="Consistent formatting for better data quality",
                    confidence=match_ratio,
                    risk_level="low",
                    reversible=True
                ))

        return suggestions

    def _detect_date_formats(self, series: pd.Series) -> List[str]:
        """Detect date formats in a string series."""
        formats_found = []
        sample = series.dropna().head(20)

        for date_pattern in self.date_patterns:
            try:
                parsed_count = 0
                for value in sample:
                    try:
                        datetime.strptime(str(value), date_pattern)
                        parsed_count += 1
                    except:
                        pass

                if parsed_count > len(sample) * 0.3:  # 30% match rate
                    formats_found.append(date_pattern)
            except:
                pass

        return formats_found

    def _needs_scaling(self, series: pd.Series) -> bool:
        """Check if numeric series needs scaling."""
        if not pd.api.types.is_numeric_dtype(series):
            return False

        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return False

        # Check if range is very large or standard deviation is high
        range_val = non_null_series.max() - non_null_series.min()
        std_val = non_null_series.std()
        mean_val = non_null_series.mean()

        # If range is > 1000 or coefficient of variation > 2
        return range_val > 1000 or (std_val / abs(mean_val) > 2 if mean_val != 0 else False)

    def _calculate_outlier_ratio(self, series: pd.Series) -> float:
        """Calculate the ratio of outliers using IQR method."""
        if not pd.api.types.is_numeric_dtype(series):
            return 0.0

        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return 0.0

        Q1 = non_null_series.quantile(0.25)
        Q3 = non_null_series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = non_null_series[(non_null_series < lower_bound) | (non_null_series > upper_bound)]
        return len(outliers) / len(non_null_series)

    def _suggest_column_merges(self, data: pd.DataFrame) -> List[TransformationSuggestion]:
        """Suggest merging related columns."""
        suggestions = []

        # Look for columns that might be parts of a single field
        columns = data.columns.tolist()

        # Check for first_name, last_name -> full_name
        if 'first_name' in columns and 'last_name' in columns:
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.COLUMN_MERGING,
                priority=TransformationPriority.LOW,
                target_columns=['first_name', 'last_name'],
                description="Merge first_name and last_name into full_name",
                rationale="Separate name columns can be combined for easier analysis",
                current_state={"separate_columns": ['first_name', 'last_name']},
                proposed_state={"merged_column": "full_name"},
                transformation_function="merge_names",
                parameters={"separator": " "},
                estimated_impact="Simplified data structure",
                confidence=0.8,
                risk_level="low",
                reversible=True
            ))

        return suggestions

    def _suggest_column_splits(self, data: pd.DataFrame) -> List[TransformationSuggestion]:
        """Suggest splitting columns that contain multiple pieces of information."""
        suggestions = []

        for column in data.columns:
            if pd.api.types.is_string_dtype(data[column]):
                # Check if column contains multiple parts separated by delimiters
                sample = data[column].dropna().head(20)

                # Check for common delimiters
                for delimiter in [',', ';', '|', ' - ']:
                    split_counts = sample.str.split(delimiter).str.len()
                    if split_counts.mode().iloc[0] > 1 if len(split_counts.mode()) > 0 else False:
                        suggestions.append(TransformationSuggestion(
                            transformation_type=TransformationType.COLUMN_SPLITTING,
                            priority=TransformationPriority.MEDIUM,
                            target_columns=[column],
                            description=f"Split column '{column}' by delimiter '{delimiter}'",
                            rationale=f"Column appears to contain multiple values separated by '{delimiter}'",
                            current_state={"single_column": column},
                            proposed_state={"split_columns": f"{column}_1, {column}_2, ..."},
                            transformation_function="str.split",
                            parameters={"separator": delimiter, "expand": True},
                            estimated_impact="Better data structure and analysis opportunities",
                            confidence=0.7,
                            risk_level="medium",
                            reversible=True
                        ))
                        break  # Only suggest one split per column

        return suggestions

    def _prioritize_suggestions(self, suggestions: List[TransformationSuggestion],
                              context: Optional[CleanupContext]) -> List[TransformationSuggestion]:
        """Prioritize and sort transformation suggestions."""
        priority_order = {
            TransformationPriority.CRITICAL: 0,
            TransformationPriority.HIGH: 1,
            TransformationPriority.MEDIUM: 2,
            TransformationPriority.LOW: 3,
            TransformationPriority.OPTIONAL: 4
        }

        # Sort by priority, then by confidence
        suggestions.sort(key=lambda s: (priority_order[s.priority], -s.confidence))

        return suggestions

    async def _create_transformation_issues(self, suggestions: List[TransformationSuggestion]) -> List[CleanupIssue]:
        """Create CleanupIssue objects from transformation suggestions."""
        issues = []

        for suggestion in suggestions:
            # Map transformation priority to cleanup severity
            severity_mapping = {
                TransformationPriority.CRITICAL: CleanupSeverity.CRITICAL,
                TransformationPriority.HIGH: CleanupSeverity.HIGH,
                TransformationPriority.MEDIUM: CleanupSeverity.MEDIUM,
                TransformationPriority.LOW: CleanupSeverity.LOW,
                TransformationPriority.OPTIONAL: CleanupSeverity.INFO
            }

            issue = CleanupIssue(
                issue_type="transformation_opportunity",
                severity=severity_mapping[suggestion.priority],
                message=suggestion.description,
                field=", ".join(suggestion.target_columns),
                row_indices=[],  # Transformations typically affect entire columns
                affected_values=[],
                suggested_action=f"Apply {suggestion.transformation_function} transformation",
                confidence=suggestion.confidence,
                estimated_impact=suggestion.estimated_impact,
                metadata={
                    "suggestion_id": suggestion.id,
                    "transformation_type": suggestion.transformation_type.value,
                    "priority": suggestion.priority.value,
                    "parameters": suggestion.parameters
                }
            )
            issues.append(issue)

        return issues

    async def _apply_transformations(self, data: pd.DataFrame, suggestions: List[TransformationSuggestion],
                                   context: Optional[CleanupContext]) -> Tuple[pd.DataFrame, int, Dict[str, int]]:
        """Apply approved transformations to the data."""
        transformed_data = data.copy()
        applied_count = 0
        summary = {}

        for suggestion in suggestions:
            # Validate suggestion has required columns
            missing_columns = [col for col in suggestion.target_columns if col not in transformed_data.columns]
            if missing_columns:
                logger.warning(f"Skipping transformation {suggestion.id}: columns {missing_columns} not found")
                continue

            # Apply transformation based on type and function
            try:
                if suggestion.transformation_function == "pd.to_numeric":
                    for column in suggestion.target_columns:
                        if pd.api.types.is_string_dtype(transformed_data[column]) or pd.api.types.is_object_dtype(transformed_data[column]):
                            transformed_data[column] = pd.to_numeric(
                                transformed_data[column],
                                errors=suggestion.parameters.get('errors', 'coerce')
                            )

                elif suggestion.transformation_function == "pd.to_datetime":
                    for column in suggestion.target_columns:
                        if pd.api.types.is_string_dtype(transformed_data[column]) or pd.api.types.is_object_dtype(transformed_data[column]):
                            transformed_data[column] = pd.to_datetime(
                                transformed_data[column],
                                errors=suggestion.parameters.get('errors', 'coerce')
                            )

                elif suggestion.transformation_function == "str.lower":
                    for column in suggestion.target_columns:
                        if pd.api.types.is_string_dtype(transformed_data[column]):
                            transformed_data[column] = transformed_data[column].str.lower()

                elif suggestion.transformation_function == "str.strip":
                    for column in suggestion.target_columns:
                        if pd.api.types.is_string_dtype(transformed_data[column]):
                            transformed_data[column] = transformed_data[column].str.strip()

                elif suggestion.transformation_function == "astype":
                    for column in suggestion.target_columns:
                        target_dtype = suggestion.parameters.get('dtype', 'category')
                        transformed_data[column] = transformed_data[column].astype(target_dtype)

                else:
                    logger.info(f"Transformation function '{suggestion.transformation_function}' not implemented, skipping")
                    continue

                applied_count += 1
                transformation_type = suggestion.transformation_type.value
                summary[transformation_type] = summary.get(transformation_type, 0) + 1

            except Exception as e:
                logger.error(f"Failed to apply transformation {suggestion.id} to columns {suggestion.target_columns}: {str(e)}")
                continue

        return transformed_data, applied_count, summary

    async def _generate_additional_recommendations(self, data: pd.DataFrame,
                                                 suggestions: List[TransformationSuggestion]) -> List[str]:
        """Generate additional recommendations based on transformation analysis."""
        recommendations = []

        if len(suggestions) > 10:
            recommendations.append("Many transformation opportunities detected. Consider applying them in batches.")

        high_priority_count = len([s for s in suggestions if s.priority == TransformationPriority.HIGH])
        if high_priority_count > 0:
            recommendations.append(f"{high_priority_count} high-priority transformations recommended for data quality improvement.")

        data_type_suggestions = [s for s in suggestions if s.transformation_type == TransformationType.DATA_TYPE_CONVERSION]
        if len(data_type_suggestions) > 0:
            recommendations.append("Data type optimizations available that can improve performance and enable better analysis.")

        return recommendations

    def get_cleanup_info(self) -> Dict[str, Any]:
        """Get information about the transformation recommender."""
        return {
            "name": "TransformationRecommender",
            "version": "1.0.0",
            "description": "Intelligent data transformation recommendation system",
            "supported_transformations": [t.value for t in self.supported_transformations],
            "text_patterns": list(self.text_patterns.keys()),
            "date_patterns": self.date_patterns,
            "capabilities": [
                "Data type optimization",
                "Text standardization",
                "Date normalization",
                "Categorical encoding",
                "Column structure analysis",
                "Cross-column transformations"
            ]
        }
