"""
Data profiling system for comprehensive data analysis and insights.

This module provides data profiling capabilities including:
- Statistical analysis and profiling
- Pattern recognition in data
- Anomaly detection algorithms
- Data lineage tracking
- Profiling recommendations
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, date
from enum import Enum
import re
import statistics
from collections import Counter
from pydantic import BaseModel, Field
import uuid

from .base import ValidatorInterface, ValidationResult, ValidationIssue, ValidationSeverity


class DataDistributionType(str, Enum):
    """Types of data distributions."""
    NORMAL = "normal"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"
    SKEWED_LEFT = "skewed_left"
    SKEWED_RIGHT = "skewed_right"
    BIMODAL = "bimodal"
    UNKNOWN = "unknown"


class PatternType(str, Enum):
    """Types of patterns that can be detected in data."""
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    IP_ADDRESS = "ip_address"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    POSTAL_CODE = "postal_code"
    DATE_ISO = "date_iso"
    TIME = "time"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    CUSTOM = "custom"


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""
    OUTLIER = "outlier"
    MISSING_PATTERN = "missing_pattern"
    FORMAT_INCONSISTENCY = "format_inconsistency"
    VALUE_INCONSISTENCY = "value_inconsistency"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    STATISTICAL_ANOMALY = "statistical_anomaly"


class ColumnProfile(BaseModel):
    """Comprehensive profile of a single column."""

    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Detected data type")
    total_count: int = Field(..., description="Total number of values")
    null_count: int = Field(default=0, description="Number of null values")
    unique_count: int = Field(default=0, description="Number of unique values")
    duplicate_count: int = Field(default=0, description="Number of duplicate values")

    # Statistical measures
    min_value: Optional[Any] = Field(None, description="Minimum value")
    max_value: Optional[Any] = Field(None, description="Maximum value")
    mean: Optional[float] = Field(None, description="Mean value (for numeric columns)")
    median: Optional[float] = Field(None, description="Median value (for numeric columns)")
    mode: Optional[Any] = Field(None, description="Most frequent value")
    std_dev: Optional[float] = Field(None, description="Standard deviation (for numeric columns)")
    variance: Optional[float] = Field(None, description="Variance (for numeric columns)")

    # Distribution analysis
    distribution_type: Optional[DataDistributionType] = Field(None, description="Detected distribution type")
    skewness: Optional[float] = Field(None, description="Skewness measure")
    kurtosis: Optional[float] = Field(None, description="Kurtosis measure")
    quartiles: Optional[Dict[str, float]] = Field(None, description="Quartile values")

    # String-specific metrics
    min_length: Optional[int] = Field(None, description="Minimum string length")
    max_length: Optional[int] = Field(None, description="Maximum string length")
    avg_length: Optional[float] = Field(None, description="Average string length")

    # Pattern analysis
    detected_patterns: List[PatternType] = Field(default_factory=list, description="Detected patterns")
    pattern_coverage: Dict[str, float] = Field(default_factory=dict, description="Pattern coverage percentages")

    # Value frequency analysis
    top_values: Dict[Any, int] = Field(default_factory=dict, description="Most frequent values and their counts")
    value_frequency_distribution: Optional[Dict[str, int]] = Field(None, description="Value frequency distribution")

    # Quality metrics
    completeness: float = Field(default=0.0, description="Percentage of non-null values")
    uniqueness: float = Field(default=0.0, description="Percentage of unique values")
    consistency: float = Field(default=0.0, description="Pattern consistency score")

    # Anomalies
    anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="Detected anomalies")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")


class DatasetProfile(BaseModel):
    """Comprehensive profile of an entire dataset."""

    name: str = Field(..., description="Dataset name")
    total_rows: int = Field(..., description="Total number of rows")
    total_columns: int = Field(..., description="Total number of columns")

    # Column profiles
    column_profiles: Dict[str, ColumnProfile] = Field(..., description="Individual column profiles")

    # Dataset-level metrics
    completeness: float = Field(default=0.0, description="Overall dataset completeness")
    consistency: float = Field(default=0.0, description="Overall dataset consistency")
    uniqueness: float = Field(default=0.0, description="Overall dataset uniqueness")

    # Relationships
    correlations: Optional[Dict[str, Dict[str, float]]] = Field(None, description="Column correlations")
    dependencies: List[Dict[str, Any]] = Field(default_factory=list, description="Detected dependencies between columns")

    # Quality issues
    quality_issues: List[ValidationIssue] = Field(default_factory=list, description="Dataset-wide quality issues")

    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    profiling_duration_ms: Optional[float] = Field(None, description="Time taken to create profile")


class ProfileResult(ValidationResult):
    """Results of data profiling operation."""

    dataset_profile: DatasetProfile = Field(..., description="Complete dataset profile")
    profiling_summary: Dict[str, Any] = Field(default_factory=dict, description="Profiling summary statistics")


class DataProfiler(ValidatorInterface):
    """Main data profiling engine."""

    def __init__(self):
        self.statistical_analyzer = StatisticalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.anomaly_detector = AnomalyDetector()

    async def validate(self, data: pd.DataFrame, **kwargs) -> ProfileResult:
        """
        Profile the provided data comprehensively.

        Args:
            data: DataFrame to profile
            **kwargs: Additional profiling parameters

        Returns:
            ProfileResult containing comprehensive data profile
        """
        start_time = datetime.utcnow()

        result = ProfileResult(
            is_valid=True,
            execution_time_ms=0,
            dataset_profile=DatasetProfile(
                name=kwargs.get('dataset_name', 'unknown'),
                total_rows=len(data),
                total_columns=len(data.columns),
                column_profiles={},
                correlations=None,
                profiling_duration_ms=None
            )
        )

        # Profile each column
        for column in data.columns:
            column_profile = await self._profile_column(data[column], column)
            result.dataset_profile.column_profiles[column] = column_profile

        # Calculate dataset-level metrics
        await self._calculate_dataset_metrics(data, result.dataset_profile)

        # Detect relationships between columns
        await self._analyze_relationships(data, result.dataset_profile)

        # Generate recommendations
        await self._generate_recommendations(result.dataset_profile)

        # Calculate execution time
        end_time = datetime.utcnow()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        result.dataset_profile.profiling_duration_ms = result.execution_time_ms

        # Create profiling summary
        result.profiling_summary = self._create_profiling_summary(result.dataset_profile)

        return result

    async def _profile_column(self, series: pd.Series, column_name: str) -> ColumnProfile:
        """Profile a single column comprehensively."""
        profile = ColumnProfile(
            name=column_name,
            data_type=str(series.dtype),
            total_count=len(series),
            null_count=series.isnull().sum(),
            unique_count=series.nunique(),
            duplicate_count=series.duplicated().sum(),
            min_value=None,
            max_value=None,
            mean=None,
            median=None,
            mode=None,
            std_dev=None,
            variance=None,
            distribution_type=None,
            skewness=None,
            kurtosis=None,
            quartiles=None,
            min_length=None,
            max_length=None,
            avg_length=None,
            value_frequency_distribution=None
        )

        # Calculate basic metrics
        profile.completeness = ((profile.total_count - profile.null_count) / profile.total_count) * 100
        profile.uniqueness = (profile.unique_count / profile.total_count) * 100 if profile.total_count > 0 else 0

        # Get non-null data for analysis
        non_null_series = series.dropna()

        if len(non_null_series) == 0:
            return profile

        # Basic statistics
        try:
            profile.min_value = non_null_series.min()
            profile.max_value = non_null_series.max()
            profile.mode = non_null_series.mode().iloc[0] if len(non_null_series.mode()) > 0 else None
        except:
            pass

        # Numeric analysis
        if pd.api.types.is_numeric_dtype(non_null_series):
            await self._analyze_numeric_column(non_null_series, profile)

        # String analysis
        if pd.api.types.is_string_dtype(non_null_series):
            await self._analyze_string_column(non_null_series, profile)

        # Pattern recognition
        profile.detected_patterns = await self.pattern_recognizer.detect_patterns(non_null_series)
        profile.pattern_coverage = await self.pattern_recognizer.calculate_pattern_coverage(non_null_series, profile.detected_patterns)

        # Value frequency analysis
        profile.top_values = dict(non_null_series.value_counts().head(10).to_dict())

        # Anomaly detection
        profile.anomalies = await self.anomaly_detector.detect_anomalies(non_null_series, column_name)

        # Pattern consistency
        profile.consistency = await self._calculate_consistency_score(non_null_series, profile)

        return profile

    async def _analyze_numeric_column(self, series: pd.Series, profile: ColumnProfile):
        """Analyze numeric column specifics."""
        try:
            try:
                val = series.mean()
                profile.mean = float(val) if pd.notna(val) and not isinstance(val, complex) else None
            except:
                profile.mean = None
            try:
                val = series.median()
                profile.median = float(val) if pd.notna(val) and not isinstance(val, complex) else None
            except:
                profile.median = None
            try:
                val = series.std()
                profile.std_dev = float(val) if pd.notna(val) and not isinstance(val, complex) else None
            except:
                profile.std_dev = None
            try:
                val = series.var()
                profile.variance = float(val) if pd.notna(val) and isinstance(val, (int, float)) and not isinstance(val, complex) else None
            except:
                profile.variance = None

            # Quartiles
            profile.quartiles = {
                "q1": float(series.quantile(0.25)),
                "q2": float(series.quantile(0.5)),
                "q3": float(series.quantile(0.75))
            }

            # Distribution analysis
            try:
                val = series.skew()
                profile.skewness = float(val) if pd.notna(val) and isinstance(val, (int, float)) and not isinstance(val, complex) else None
            except:
                profile.skewness = None
            try:
                val = series.kurtosis()
                profile.kurtosis = float(val) if pd.notna(val) and isinstance(val, (int, float)) and not isinstance(val, complex) else None
            except:
                profile.kurtosis = None
            profile.distribution_type = await self.statistical_analyzer.detect_distribution(series)

        except Exception:
            # Handle cases where statistical operations fail
            pass

    async def _analyze_string_column(self, series: pd.Series, profile: ColumnProfile):
        """Analyze string column specifics."""
        try:
            str_lengths = series.astype(str).str.len()
            profile.min_length = int(str_lengths.min())
            profile.max_length = int(str_lengths.max())
            profile.avg_length = float(str_lengths.mean())
        except Exception:
            pass

    async def _calculate_consistency_score(self, series: pd.Series, profile: ColumnProfile) -> float:
        """Calculate consistency score based on pattern adherence."""
        if not profile.detected_patterns:
            return 100.0  # No patterns to violate

        total_score = 0.0
        for pattern in profile.detected_patterns:
            coverage = profile.pattern_coverage.get(pattern.value, 0.0)
            total_score += coverage

        return total_score / len(profile.detected_patterns) if profile.detected_patterns else 100.0

    async def _calculate_dataset_metrics(self, data: pd.DataFrame, profile: DatasetProfile):
        """Calculate dataset-level quality metrics."""
        total_cells = data.shape[0] * data.shape[1]
        null_cells = data.isnull().sum().sum()

        profile.completeness = ((total_cells - null_cells) / total_cells) * 100 if total_cells > 0 else 0

        # Average column-level metrics
        if profile.column_profiles:
            profile.consistency = sum(cp.consistency for cp in profile.column_profiles.values()) / len(profile.column_profiles)
            profile.uniqueness = sum(cp.uniqueness for cp in profile.column_profiles.values()) / len(profile.column_profiles)

    async def _analyze_relationships(self, data: pd.DataFrame, profile: DatasetProfile):
        """Analyze relationships between columns."""
        numeric_data = data.select_dtypes(include=[np.number])

        if len(numeric_data.columns) > 1:
            try:
                # Calculate correlations
                corr_matrix = numeric_data.corr()
                profile.correlations = {}

                for col1 in corr_matrix.columns:
                    profile.correlations[col1] = {}
                    for col2 in corr_matrix.columns:
                        if col1 != col2:
                            correlation = corr_matrix.loc[col1, col2]
                            if not pd.isna(correlation):
                                try:
                                    val = float(correlation) if pd.notna(correlation) and isinstance(correlation, (int, float)) and not isinstance(correlation, complex) else None
                                    if val is not None:
                                        profile.correlations[col1][col2] = val
                                except:
                                    pass

                # Detect strong correlations
                for col1 in profile.correlations:
                    for col2, correlation in profile.correlations[col1].items():
                        if abs(correlation) > 0.8:
                            profile.dependencies.append({
                                "type": "correlation",
                                "column1": col1,
                                "column2": col2,
                                "strength": correlation,
                                "description": f"Strong correlation ({correlation:.2f}) between {col1} and {col2}"
                            })
            except Exception:
                pass

    async def _generate_recommendations(self, profile: DatasetProfile):
        """Generate improvement recommendations based on profiling results."""
        recommendations = []

        # Check for columns with high null rates
        for col_name, col_profile in profile.column_profiles.items():
            if col_profile.completeness < 70:
                recommendations.append(f"Column '{col_name}' has low completeness ({col_profile.completeness:.1f}%). Consider data cleaning or imputation.")

            if col_profile.uniqueness < 1 and col_profile.total_count > 100:
                recommendations.append(f"Column '{col_name}' has many duplicate values. Consider if this is expected.")

            if col_profile.consistency < 80:
                recommendations.append(f"Column '{col_name}' has inconsistent patterns. Consider standardization.")

            if len(col_profile.anomalies) > 0:
                recommendations.append(f"Column '{col_name}' has {len(col_profile.anomalies)} anomalies. Review for data quality issues.")

        # Dataset-level recommendations
        if profile.completeness < 80:
            recommendations.append("Dataset has low overall completeness. Consider comprehensive data cleaning.")

        if profile.consistency < 70:
            recommendations.append("Dataset has consistency issues across multiple columns. Implement data standardization.")

        profile.recommendations = recommendations

    def _create_profiling_summary(self, profile: DatasetProfile) -> Dict[str, Any]:
        """Create a summary of profiling results."""
        return {
            "dataset_size": f"{profile.total_rows:,} rows x {profile.total_columns} columns",
            "overall_quality": {
                "completeness": f"{profile.completeness:.1f}%",
                "consistency": f"{profile.consistency:.1f}%",
                "uniqueness": f"{profile.uniqueness:.1f}%"
            },
            "column_types": {
                col_profile.data_type: len([cp for cp in profile.column_profiles.values() if cp.data_type == col_profile.data_type])
                for col_profile in profile.column_profiles.values()
            },
            "quality_issues_count": len(profile.quality_issues),
            "relationships_found": len(profile.dependencies),
            "recommendations_count": len(profile.recommendations)
        }

    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this validator."""
        return {
            "name": "DataProfiler",
            "version": "1.0.0",
            "description": "Comprehensive data profiling and analysis engine",
            "supported_features": [
                "Statistical analysis",
                "Pattern recognition",
                "Anomaly detection",
                "Relationship analysis",
                "Quality recommendations"
            ]
        }


class StatisticalAnalyzer:
    """Performs statistical analysis on data."""

    async def detect_distribution(self, series: pd.Series) -> DataDistributionType:
        """Detect the distribution type of numeric data."""
        try:
            if len(series) < 10:
                return DataDistributionType.UNKNOWN

            # Calculate distribution metrics
            skewness = series.skew()
            kurtosis = series.kurtosis()

            # Simple distribution classification
            if isinstance(skewness, (int, float)) and isinstance(kurtosis, (int, float)) and abs(skewness) < 0.5 and abs(kurtosis) < 1:
                return DataDistributionType.NORMAL
            elif isinstance(skewness, (int, float)) and skewness > 1:
                return DataDistributionType.SKEWED_RIGHT
            elif isinstance(skewness, (int, float)) and skewness < -1:
                return DataDistributionType.SKEWED_LEFT
            elif isinstance(kurtosis, (int, float)) and kurtosis > 3:
                return DataDistributionType.BIMODAL
            else:
                return DataDistributionType.UNKNOWN

        except Exception:
            return DataDistributionType.UNKNOWN


class PatternRecognizer:
    """Recognizes patterns in data."""

    def __init__(self):
        self.patterns = {
            PatternType.EMAIL: r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            PatternType.PHONE: r'^(\+?1-?)?(\([0-9]{3}\)|[0-9]{3})[-.]?[0-9]{3}[-.]?[0-9]{4}$',
            PatternType.URL: r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
            PatternType.IP_ADDRESS: r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            PatternType.CREDIT_CARD: r'^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})$',
            PatternType.SSN: r'^\d{3}-?\d{2}-?\d{4}$',
            PatternType.POSTAL_CODE: r'^[0-9]{5}(?:-[0-9]{4})?$',
            PatternType.DATE_ISO: r'^\d{4}-\d{2}-\d{2}$',
            PatternType.TIME: r'^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$',
            PatternType.CURRENCY: r'^\$?[0-9]{1,3}(,[0-9]{3})*(\.[0-9]{2})?$',
            PatternType.PERCENTAGE: r'^[0-9]{1,3}(\.[0-9]{1,2})?%$',
        }

    async def detect_patterns(self, series: pd.Series) -> List[PatternType]:
        """Detect patterns in a data series."""
        detected = []

        # Convert to string for pattern matching
        str_series = series.astype(str)

        for pattern_type, regex in self.patterns.items():
            matches = str_series.str.match(regex, na=False).sum()
            match_ratio = matches / len(str_series) if len(str_series) > 0 else 0

            # Consider pattern detected if >50% of values match
            if match_ratio > 0.5:
                detected.append(pattern_type)

        return detected

    async def calculate_pattern_coverage(self, series: pd.Series, patterns: List[PatternType]) -> Dict[str, float]:
        """Calculate coverage percentage for each detected pattern."""
        coverage = {}
        str_series = series.astype(str)

        for pattern_type in patterns:
            regex = self.patterns.get(pattern_type)
            if regex:
                matches = str_series.str.match(regex, na=False).sum()
                coverage[pattern_type.value] = (matches / len(str_series)) * 100 if len(str_series) > 0 else 0

        return coverage


class AnomalyDetector:
    """Detects anomalies in data."""

    async def detect_anomalies(self, series: pd.Series, column_name: str) -> List[Dict[str, Any]]:
        """Detect various types of anomalies in data."""
        anomalies = []

        # Detect outliers in numeric data
        if pd.api.types.is_numeric_dtype(series):
            outliers = await self._detect_statistical_outliers(series, column_name)
            anomalies.extend(outliers)

        # Detect format inconsistencies
        format_anomalies = await self._detect_format_inconsistencies(series, column_name)
        anomalies.extend(format_anomalies)

        return anomalies

    async def _detect_statistical_outliers(self, series: pd.Series, column_name: str) -> List[Dict[str, Any]]:
        """Detect statistical outliers using IQR method."""
        anomalies = []

        try:
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = series[(series < lower_bound) | (series > upper_bound)]

            for idx, value in outliers.items():
                anomalies.append({
                    "type": AnomalyType.OUTLIER.value,
                    "row": idx,
                    "value": value,
                    "description": f"Statistical outlier in column '{column_name}' (value: {value})",
                    "severity": "medium"
                })

        except Exception:
            pass

        return anomalies

    async def _detect_format_inconsistencies(self, series: pd.Series, column_name: str) -> List[Dict[str, Any]]:
        """Detect format inconsistencies in string data."""
        anomalies = []

        if not pd.api.types.is_string_dtype(series):
            return anomalies

        # Analyze string lengths
        str_series = series.astype(str)
        lengths = str_series.str.len()

        # Detect unusually short or long strings
        mean_length = lengths.mean()
        std_length = lengths.std()

        if std_length > 0:
            for idx, length in lengths.items():
                if abs(length - mean_length) > 3 * std_length:
                    anomalies.append({
                        "type": AnomalyType.FORMAT_INCONSISTENCY.value,
                        "row": idx,
                        "value": str(series.iloc[int(idx)]) if isinstance(idx, (int, str)) and str(idx).isdigit() else None,
                        "description": f"Unusual string length in column '{column_name}' (length: {length}, expected around: {mean_length:.0f})",
                        "severity": "low"
                    })

        return anomalies


class ProfilingRecommendations:
    """Generates recommendations based on profiling results."""

    @staticmethod
    def generate_data_quality_recommendations(profile: DatasetProfile) -> List[str]:
        """Generate data quality improvement recommendations."""
        recommendations = []

        # Analyze each column
        for col_name, col_profile in profile.column_profiles.items():
            if col_profile.completeness < 50:
                recommendations.append(f"Column '{col_name}' has very low completeness. Consider removing or investigating data source.")
            elif col_profile.completeness < 80:
                recommendations.append(f"Column '{col_name}' has moderate completeness issues. Implement data cleaning strategies.")

            if col_profile.uniqueness > 95 and col_profile.total_count > 1000:
                recommendations.append(f"Column '{col_name}' appears to be a unique identifier. Consider using as primary key.")

            if len(col_profile.anomalies) > col_profile.total_count * 0.1:
                recommendations.append(f"Column '{col_name}' has many anomalies. Implement data validation rules.")

        return recommendations

    @staticmethod
    def generate_performance_recommendations(profile: DatasetProfile) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        if profile.total_rows > 1000000:
            recommendations.append("Large dataset detected. Consider implementing data partitioning strategies.")

        if profile.total_columns > 100:
            recommendations.append("Wide dataset detected. Consider column selection or dimensionality reduction.")

        # Check for highly correlated columns
        if profile.correlations:
            high_corr_pairs = []
            for col1, correlations in profile.correlations.items():
                for col2, corr in correlations.items():
                    if abs(corr) > 0.95:
                        high_corr_pairs.append((col1, col2))

            if high_corr_pairs:
                recommendations.append(f"Found {len(high_corr_pairs)} highly correlated column pairs. Consider removing redundant columns.")

        return recommendations
