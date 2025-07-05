"""
Outlier detection and handling for intelligent data cleanup.

This module provides comprehensive outlier detection and handling capabilities including:
- Multiple outlier detection methods (statistical, ML-based)
- Various handling strategies (removal, transformation, capping)
- Confidence scoring and impact assessment
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
import logging
from pydantic import BaseModel, Field

from .base import CleanupInterface, CleanupResult, CleanupIssue, CleanupSeverity, CleanupContext, CleanupStrategy

logger = logging.getLogger(__name__)


class OutlierDetectionMethod(str, Enum):
    """Available outlier detection methods."""
    IQR = "iqr"  # Interquartile Range
    Z_SCORE = "z_score"  # Z-Score (standard deviations)
    MODIFIED_Z_SCORE = "modified_z_score"  # Modified Z-Score using median
    ISOLATION_FOREST = "isolation_forest"  # ML-based isolation forest
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"  # LOF algorithm
    STATISTICAL_COMBO = "statistical_combo"  # Combination of statistical methods
    DOMAIN_SPECIFIC = "domain_specific"  # Domain-specific rules


class OutlierHandlingStrategy(str, Enum):
    """Strategies for handling detected outliers."""
    REMOVE = "remove"  # Remove outlier rows
    CAP = "cap"  # Cap values to percentiles
    TRANSFORM = "transform"  # Apply transformations (log, sqrt, etc.)
    REPLACE_MEDIAN = "replace_median"  # Replace with median
    REPLACE_MEAN = "replace_mean"  # Replace with mean
    REPLACE_MODE = "replace_mode"  # Replace with mode
    INTERPOLATE = "interpolate"  # Interpolate values
    FLAG_ONLY = "flag_only"  # Only flag, don't modify data


class OutlierResult(CleanupResult):
    """Specialized result for outlier handling operations."""

    detection_method: OutlierDetectionMethod = Field(..., description="Method used for detection")
    handling_strategy: OutlierHandlingStrategy = Field(..., description="Strategy used for handling")
    outliers_detected: int = Field(default=0, description="Number of outliers detected")
    outliers_handled: int = Field(default=0, description="Number of outliers handled")
    detection_thresholds: Dict[str, float] = Field(default_factory=dict, description="Thresholds used for detection")
    column_outlier_counts: Dict[str, int] = Field(default_factory=dict, description="Outlier count per column")


class OutlierHandler(CleanupInterface):
    """Comprehensive outlier detection and handling system."""

    def __init__(self):
        self.supported_methods = list(OutlierDetectionMethod)
        self.supported_strategies = list(OutlierHandlingStrategy)
        self.default_thresholds = {
            OutlierDetectionMethod.Z_SCORE: 3.0,
            OutlierDetectionMethod.MODIFIED_Z_SCORE: 3.5,
            OutlierDetectionMethod.IQR: 1.5,
            OutlierDetectionMethod.ISOLATION_FOREST: 0.1
        }

    async def clean(self, data: pd.DataFrame, context: Optional[CleanupContext] = None, **kwargs) -> OutlierResult:
        """
        Detect and handle outliers in the provided DataFrame.

        Args:
            data: DataFrame to clean
            context: Cleanup context with preferences
            **kwargs: Additional parameters (method, strategy, thresholds)

        Returns:
            OutlierResult with cleaned data and operation details
        """
        start_time = datetime.utcnow()

        # Validate input
        if not self.validate_input(data):
            return OutlierResult(
                is_successful=False,
                cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                detection_method=OutlierDetectionMethod.IQR,
                handling_strategy=OutlierHandlingStrategy.FLAG_ONLY,
                cleaned_data=data.copy(),
                rollback_info={}
            )

        # Extract parameters
        method = kwargs.get('method', OutlierDetectionMethod.IQR)
        strategy = kwargs.get('strategy', OutlierHandlingStrategy.FLAG_ONLY)
        columns = kwargs.get('columns', None)  # Specific columns to analyze
        thresholds = kwargs.get('thresholds', {})

        # Use context strategy if provided
        if context and context.cleanup_strategy:
            if context.cleanup_strategy == CleanupStrategy.CONSERVATIVE:
                strategy = OutlierHandlingStrategy.FLAG_ONLY
            elif context.cleanup_strategy == CleanupStrategy.AUTOMATIC:
                strategy = kwargs.get('strategy', OutlierHandlingStrategy.CAP)

        result = OutlierResult(
            is_successful=True,
            cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
            detection_method=method,
            handling_strategy=strategy,
            cleaned_data=data.copy(),
            detection_thresholds=thresholds,
            rollback_info={}
        )

        try:
            # Select numeric columns for outlier detection
            numeric_columns = self._get_numeric_columns(data, columns)

            if not numeric_columns:
                logger.warning("No numeric columns found for outlier detection")
                return result

            # Detect outliers
            outlier_info = await self._detect_outliers(data, numeric_columns, method, thresholds)

            # Create cleanup issues
            issues = await self._create_outlier_issues(data, outlier_info, method)
            result.issues_found = issues
            result.outliers_detected = len([idx for outliers in outlier_info.values() for idx in outliers])

            # Calculate column-wise outlier counts
            for column, outlier_indices in outlier_info.items():
                result.column_outlier_counts[column] = len(outlier_indices)

            # Handle outliers based on strategy
            if strategy != OutlierHandlingStrategy.FLAG_ONLY:
                handled_data, handled_count = await self._handle_outliers(
                    data, outlier_info, strategy, context
                )
                result.cleaned_data = handled_data
                result.outliers_handled = handled_count
                result.rows_affected = handled_count

                # Mark issues as resolved
                for issue in issues[:handled_count]:
                    result.mark_issue_resolved(issue.id)

            # Calculate execution time
            end_time = datetime.utcnow()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Generate additional recommendations
            result.additional_recommendations = await self._generate_recommendations(
                data, outlier_info, method, strategy
            )

        except Exception as e:
            logger.error(f"Outlier handling failed: {str(e)}")
            result.is_successful = False
            result.add_issue(CleanupIssue(
                issue_type="outlier_processing_error",
                severity=CleanupSeverity.CRITICAL,
                message=f"Outlier processing failed: {str(e)}",
                field="",
                suggested_action="Review data format and try different detection method",
                confidence=1.0,
                estimated_impact="Processing cannot continue"
            ))

        return result

    async def analyze_data(self, data: pd.DataFrame, context: Optional[CleanupContext] = None) -> List[CleanupIssue]:
        """Analyze data to identify outliers without handling them."""
        numeric_columns = self._get_numeric_columns(data)
        if not numeric_columns:
            return []

        # Use multiple methods for comprehensive analysis
        methods = [OutlierDetectionMethod.IQR, OutlierDetectionMethod.Z_SCORE, OutlierDetectionMethod.MODIFIED_Z_SCORE]
        all_issues = []

        for method in methods:
            try:
                outlier_info = await self._detect_outliers(data, numeric_columns, method, {})
                issues = await self._create_outlier_issues(data, outlier_info, method)
                all_issues.extend(issues)
            except Exception as e:
                logger.warning(f"Outlier analysis with {method} failed: {str(e)}")

        # Remove duplicates based on same row/column combinations
        unique_issues = self._deduplicate_issues(all_issues)
        return unique_issues

    def _get_numeric_columns(self, data: pd.DataFrame, specified_columns: Optional[List[str]] = None) -> List[str]:
        """Get numeric columns suitable for outlier detection."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()

        if specified_columns:
            numeric_columns = [col for col in specified_columns if col in numeric_columns]

        return numeric_columns

    async def _detect_outliers(self, data: pd.DataFrame, columns: List[str],
                             method: OutlierDetectionMethod, thresholds: Dict[str, float]) -> Dict[str, List[int]]:
        """Detect outliers using the specified method."""
        outlier_info = {}

        for column in columns:
            try:
                outlier_indices = []
                column_data = data[column].dropna()

                if len(column_data) == 0:
                    outlier_info[column] = []
                    continue

                if method == OutlierDetectionMethod.IQR:
                    outlier_indices = self._detect_iqr_outliers(
                        column_data, thresholds.get('iqr_factor', self.default_thresholds[method])
                    )

                elif method == OutlierDetectionMethod.Z_SCORE:
                    outlier_indices = self._detect_zscore_outliers(
                        column_data, thresholds.get('z_threshold', self.default_thresholds[method])
                    )

                elif method == OutlierDetectionMethod.MODIFIED_Z_SCORE:
                    outlier_indices = self._detect_modified_zscore_outliers(
                        column_data, thresholds.get('modified_z_threshold', self.default_thresholds[method])
                    )

                elif method == OutlierDetectionMethod.ISOLATION_FOREST:
                    outlier_indices = self._detect_isolation_forest_outliers(
                        column_data, thresholds.get('contamination', self.default_thresholds[method])
                    )

                outlier_info[column] = outlier_indices

            except Exception as e:
                logger.warning(f"Outlier detection failed for column {column}: {str(e)}")
                outlier_info[column] = []

        return outlier_info

    def _detect_iqr_outliers(self, series: pd.Series, factor: float = 1.5) -> List[int]:
        """Detect outliers using Interquartile Range method."""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR

        outliers = series[(series < lower_bound) | (series > upper_bound)]
        return outliers.index.tolist()

    def _detect_zscore_outliers(self, series: pd.Series, threshold: float = 3.0) -> List[int]:
        """Detect outliers using Z-Score method."""
        mean_val = series.mean()
        std_val = series.std()
        if std_val == 0:
            return []  # No outliers if no variation
        z_scores = np.abs((series - mean_val) / std_val)
        outliers = series[z_scores > threshold]
        return outliers.index.tolist()

    def _detect_modified_zscore_outliers(self, series: pd.Series, threshold: float = 3.5) -> List[int]:
        """Detect outliers using Modified Z-Score method (using median)."""
        median = series.median()
        mad = np.median(np.abs(series - median))  # Median Absolute Deviation

        if mad == 0:
            return []  # No outliers if MAD is 0

        modified_z_scores = 0.6745 * (series - median) / float(mad)
        outliers = series[np.abs(modified_z_scores) > threshold]
        return outliers.index.tolist()

    def _detect_isolation_forest_outliers(self, series: pd.Series, contamination: float = 0.1) -> List[int]:
        """Detect outliers using Isolation Forest method."""
        try:
            # Reshape for sklearn
            X = np.array(series).reshape(-1, 1)

            # Fit Isolation Forest
            iso_forest = IsolationForest(contamination=str(contamination), random_state=42)
            outlier_labels = iso_forest.fit_predict(X)

            # Get outlier indices
            outlier_indices = series.index[outlier_labels == -1].tolist()
            return outlier_indices

        except Exception:
            # Fallback to IQR if Isolation Forest fails
            return self._detect_iqr_outliers(series)

    async def _create_outlier_issues(self, data: pd.DataFrame, outlier_info: Dict[str, List[int]],
                                   method: OutlierDetectionMethod) -> List[CleanupIssue]:
        """Create CleanupIssue objects for detected outliers."""
        issues = []

        for column, outlier_indices in outlier_info.items():
            if not outlier_indices:
                continue

            # Group consecutive outliers for better reporting
            outlier_groups = self._group_consecutive_indices(outlier_indices)

            for group in outlier_groups:
                affected_values = data.loc[group, column].tolist()

                # Calculate confidence based on how extreme the outliers are
                confidence = self._calculate_outlier_confidence(data[column], group, method)

                # Determine severity based on number of outliers and confidence
                severity = self._determine_outlier_severity(len(group), len(data), confidence)

                issue = CleanupIssue(
                    issue_type="outlier",
                    severity=severity,
                    message=f"Detected {len(group)} outlier(s) in column '{column}' using {method.value} method",
                    field=column,
                    row_indices=group,
                    affected_values=affected_values,
                    suggested_action=f"Consider capping, transforming, or removing outliers in '{column}'",
                    confidence=confidence,
                    estimated_impact=f"Affects {len(group)} rows ({(len(group)/len(data)*100):.1f}% of data)",
                    metadata={
                        "detection_method": method.value,
                        "outlier_count": len(group),
                        "column_stats": {
                            "mean": float(data[column].mean()),
                            "median": float(data[column].median()),
                            "std": float(data[column].std())
                        }
                    }
                )
                issues.append(issue)

        return issues

    def _group_consecutive_indices(self, indices: List[int]) -> List[List[int]]:
        """Group consecutive indices together."""
        if not indices:
            return []

        sorted_indices = sorted(indices)
        groups = []
        current_group = [sorted_indices[0]]

        for i in range(1, len(sorted_indices)):
            if sorted_indices[i] - sorted_indices[i-1] == 1:
                current_group.append(sorted_indices[i])
            else:
                groups.append(current_group)
                current_group = [sorted_indices[i]]

        groups.append(current_group)
        return groups

    def _calculate_outlier_confidence(self, series: pd.Series, outlier_indices: List[int],
                                    method: OutlierDetectionMethod) -> float:
        """Calculate confidence score for outlier detection."""
        if not outlier_indices:
            return 0.0

        outlier_values = series.loc[outlier_indices]
        series_clean = series.drop(outlier_indices)

        if len(series_clean) == 0:
            return 0.5  # Medium confidence if all values are outliers

        # Calculate how far outliers are from the main distribution
        if method == OutlierDetectionMethod.IQR:
            Q1 = series_clean.quantile(0.25)
            Q3 = series_clean.quantile(0.75)
            IQR = Q3 - Q1
            distances = []
            for val in outlier_values:
                if val < Q1:
                    distances.append((Q1 - val) / IQR if IQR > 0 else 1)
                else:
                    distances.append((val - Q3) / IQR if IQR > 0 else 1)
            avg_distance = np.mean(distances)
            # Map distance to confidence (higher distance = higher confidence)
            confidence = min(1.0, avg_distance / 3.0)  # Normalize to 0-1

        else:  # Z-Score based methods
            mean_val = series_clean.mean()
            std_val = series_clean.std()
            if std_val > 0:
                z_scores = np.abs((outlier_values - mean_val) / std_val)
                avg_z_score = np.mean(z_scores)
                confidence = min(1.0, avg_z_score / 5.0)  # Normalize to 0-1
            else:
                confidence = 0.5

        return float(confidence)

    def _determine_outlier_severity(self, outlier_count: int, total_rows: int, confidence: float) -> CleanupSeverity:
        """Determine severity of outliers based on count, proportion, and confidence."""
        proportion = outlier_count / total_rows if total_rows > 0 else 0

        if confidence > 0.8 and proportion > 0.1:
            return CleanupSeverity.HIGH
        elif confidence > 0.6 and proportion > 0.05:
            return CleanupSeverity.MEDIUM
        elif confidence > 0.4:
            return CleanupSeverity.LOW
        else:
            return CleanupSeverity.INFO

    async def _handle_outliers(self, data: pd.DataFrame, outlier_info: Dict[str, List[int]],
                             strategy: OutlierHandlingStrategy, context: Optional[CleanupContext]) -> Tuple[pd.DataFrame, int]:
        """Handle detected outliers based on the specified strategy."""
        cleaned_data = data.copy()
        total_handled = 0

        for column, outlier_indices in outlier_info.items():
            if not outlier_indices:
                continue

            column_data = cleaned_data[column]
            handled_count = 0

            if strategy == OutlierHandlingStrategy.REMOVE:
                cleaned_data = cleaned_data.drop(outlier_indices)
                handled_count = len(outlier_indices)

            elif strategy == OutlierHandlingStrategy.CAP:
                # Cap to 5th and 95th percentiles
                lower_cap = column_data.quantile(0.05)
                upper_cap = column_data.quantile(0.95)
                cleaned_data.loc[outlier_indices, column] = np.clip(
                    cleaned_data.loc[outlier_indices, column], lower_cap, upper_cap
                )
                handled_count = len(outlier_indices)

            elif strategy == OutlierHandlingStrategy.REPLACE_MEDIAN:
                median_value = column_data.median()
                cleaned_data.loc[outlier_indices, column] = median_value
                handled_count = len(outlier_indices)

            elif strategy == OutlierHandlingStrategy.REPLACE_MEAN:
                mean_value = column_data.mean()
                cleaned_data.loc[outlier_indices, column] = mean_value
                handled_count = len(outlier_indices)

            elif strategy == OutlierHandlingStrategy.INTERPOLATE:
                # Use interpolation for outliers
                for idx in outlier_indices:
                    if idx > 0 and idx < len(cleaned_data) - 1:
                        prev_val = cleaned_data.iloc[idx-1][column]
                        next_val = cleaned_data.iloc[idx+1][column]
                        if pd.notna(prev_val) and pd.notna(next_val):
                            cleaned_data.loc[idx, column] = (prev_val + next_val) / 2
                            handled_count += 1

            total_handled += handled_count

        return cleaned_data, total_handled

    async def _generate_recommendations(self, data: pd.DataFrame, outlier_info: Dict[str, List[int]],
                                      method: OutlierDetectionMethod, strategy: OutlierHandlingStrategy) -> List[str]:
        """Generate additional recommendations based on outlier analysis."""
        recommendations = []

        total_outliers = sum(len(indices) for indices in outlier_info.values())
        total_rows = len(data)
        outlier_percentage = (total_outliers / total_rows) * 100 if total_rows > 0 else 0

        if outlier_percentage > 20:
            recommendations.append("High percentage of outliers detected. Consider reviewing data collection process.")

        if outlier_percentage > 10:
            recommendations.append("Consider using robust statistical methods that are less sensitive to outliers.")

        if strategy == OutlierHandlingStrategy.FLAG_ONLY:
            recommendations.append("Outliers have been flagged. Consider applying automated handling if appropriate.")

        # Column-specific recommendations
        for column, indices in outlier_info.items():
            if len(indices) > 0:
                col_percentage = (len(indices) / total_rows) * 100
                if col_percentage > 15:
                    recommendations.append(f"Column '{column}' has {col_percentage:.1f}% outliers. Consider data transformation or domain expertise review.")

        return recommendations

    def _deduplicate_issues(self, issues: List[CleanupIssue]) -> List[CleanupIssue]:
        """Remove duplicate issues that affect the same data points."""
        seen_combinations = set()
        unique_issues = []

        for issue in issues:
            # Create identifier based on field and row indices
            combination = (issue.field, tuple(sorted(issue.row_indices)))
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_issues.append(issue)

        return unique_issues

    def get_cleanup_info(self) -> Dict[str, Any]:
        """Get information about the outlier handler."""
        return {
            "name": "OutlierHandler",
            "version": "1.0.0",
            "description": "Comprehensive outlier detection and handling system",
            "supported_detection_methods": [method.value for method in self.supported_methods],
            "supported_handling_strategies": [strategy.value for strategy in self.supported_strategies],
            "default_thresholds": {k.value: v for k, v in self.default_thresholds.items()},
            "capabilities": [
                "Multi-method outlier detection",
                "Configurable handling strategies",
                "Confidence scoring",
                "Impact assessment",
                "Batch and column-specific processing"
            ]
        }
