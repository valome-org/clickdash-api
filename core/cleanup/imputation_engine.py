"""
Missing data imputation engine for intelligent data cleanup.

This module provides comprehensive missing data imputation capabilities including:
- Statistical imputation methods (mean, median, mode)
- Advanced imputation techniques (KNN, iterative, model-based)
- Pattern-aware imputation strategies
- Domain-specific imputation rules
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from sklearn.impute import KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
import logging
from pydantic import BaseModel, Field

from .base import CleanupInterface, CleanupResult, CleanupIssue, CleanupSeverity, CleanupContext, CleanupStrategy

logger = logging.getLogger(__name__)


class ImputationMethod(str, Enum):
    """Available imputation methods."""
    MEAN = "mean"  # Mean value for numeric columns
    MEDIAN = "median"  # Median value for numeric columns
    MODE = "mode"  # Most frequent value
    FORWARD_FILL = "forward_fill"  # Forward fill (last observation carried forward)
    BACKWARD_FILL = "backward_fill"  # Backward fill
    LINEAR_INTERPOLATION = "linear_interpolation"  # Linear interpolation
    KNN = "knn"  # K-Nearest Neighbors imputation
    ITERATIVE = "iterative"  # Iterative imputation (MICE)
    RANDOM_FOREST = "random_forest"  # Random Forest-based imputation
    CONSTANT = "constant"  # Fill with constant value
    DROP = "drop"  # Drop rows/columns with missing values


class ImputationStrategy(str, Enum):
    """Strategies for handling missing data patterns."""
    AUTOMATIC = "automatic"  # Automatically choose best method per column
    CONSERVATIVE = "conservative"  # Use simple, safe methods
    AGGRESSIVE = "aggressive"  # Use advanced ML-based methods
    DOMAIN_SPECIFIC = "domain_specific"  # Use domain knowledge
    PATTERN_AWARE = "pattern_aware"  # Consider missing data patterns


class MissingDataPattern(str, Enum):
    """Types of missing data patterns."""
    MCAR = "mcar"  # Missing Completely At Random
    MAR = "mar"  # Missing At Random
    MNAR = "mnar"  # Missing Not At Random
    SYSTEMATIC = "systematic"  # Systematic missing pattern


class ImputationResult(CleanupResult):
    """Specialized result for imputation operations."""

    imputation_method: ImputationMethod = Field(..., description="Primary imputation method used")
    imputation_strategy: ImputationStrategy = Field(..., description="Strategy used for imputation")
    missing_data_pattern: Optional[MissingDataPattern] = Field(None, description="Detected missing data pattern")
    values_imputed: int = Field(default=0, description="Number of missing values imputed")
    columns_imputed: List[str] = Field(default_factory=list, description="Columns that had values imputed")
    imputation_quality_score: float = Field(default=0.0, description="Quality score of imputation (0-1)")
    method_per_column: Dict[str, str] = Field(default_factory=dict, description="Method used per column")


class ImputationEngine(CleanupInterface):
    """Comprehensive missing data imputation system."""

    def __init__(self):
        self.supported_methods = list(ImputationMethod)
        self.supported_strategies = list(ImputationStrategy)
        self.encoders = {}  # Store label encoders for categorical columns
        self.scalers = {}   # Store scalers for numeric columns

    async def clean(self, data: pd.DataFrame, context: Optional[CleanupContext] = None, **kwargs) -> ImputationResult:
        """
        Impute missing values in the provided DataFrame.

        Args:
            data: DataFrame to clean
            context: Cleanup context with preferences
            **kwargs: Additional parameters (method, strategy, fill_value)

        Returns:
            ImputationResult with imputed data and operation details
        """
        start_time = datetime.utcnow()

        # Validate input
        try:
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Input must be a pandas DataFrame")

            if hasattr(data, 'empty') and data.empty:
                logger.warning("Input DataFrame is empty")
                return ImputationResult(
                    is_successful=True,
                    cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                    imputation_method=ImputationMethod.MEDIAN,
                    imputation_strategy=ImputationStrategy.CONSERVATIVE,
                    cleaned_data=data.copy(),
                    rollback_info={},
                    missing_data_pattern=None
                )

            if not self.validate_input(data):
                return ImputationResult(
                    is_successful=False,
                    cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                    imputation_method=ImputationMethod.MEDIAN,
                    imputation_strategy=ImputationStrategy.CONSERVATIVE,
                    cleaned_data=data.copy(),
                    rollback_info={},
                    missing_data_pattern=None
                )

        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return ImputationResult(
                is_successful=False,
                cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                imputation_method=ImputationMethod.MEDIAN,
                imputation_strategy=ImputationStrategy.CONSERVATIVE,
                cleaned_data=data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(),
                rollback_info={},
                missing_data_pattern=None
            )

        # Extract parameters
        method = kwargs.get('method', ImputationMethod.MEDIAN)
        strategy = kwargs.get('strategy', ImputationStrategy.AUTOMATIC)
        fill_value = kwargs.get('fill_value', None)
        columns = kwargs.get('columns', None)  # Specific columns to impute

        # Use context strategy if provided
        if context and context.cleanup_strategy:
            if context.cleanup_strategy == CleanupStrategy.CONSERVATIVE:
                strategy = ImputationStrategy.CONSERVATIVE
            elif context.cleanup_strategy == CleanupStrategy.AUTOMATIC:
                strategy = ImputationStrategy.AUTOMATIC

        result = ImputationResult(
            is_successful=True,
            cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
            imputation_method=method,
            imputation_strategy=strategy,
            cleaned_data=data.copy(),
            rollback_info={},
            missing_data_pattern=None
        )

        try:
            # Analyze missing data patterns
            missing_pattern = await self._analyze_missing_patterns(data)
            result.missing_data_pattern = missing_pattern

            # Identify columns with missing values
            missing_info = await self._identify_missing_data(data, columns)
            if not missing_info:
                logger.info("No missing data found")
                return result

            # Create cleanup issues for missing data
            issues = await self._create_missing_data_issues(data, missing_info)
            result.issues_found = issues

            # Determine imputation methods per column
            column_methods = await self._determine_imputation_methods(
                data, missing_info, strategy, method
            )
            result.method_per_column = column_methods

            # Perform imputation
            imputed_data, imputation_stats = await self._perform_imputation(
                data, missing_info, column_methods, fill_value
            )

            result.cleaned_data = imputed_data
            result.values_imputed = imputation_stats['total_imputed']
            result.columns_imputed = imputation_stats['columns_imputed']
            result.rows_affected = imputation_stats['rows_affected']

            # Calculate imputation quality score
            result.imputation_quality_score = await self._calculate_imputation_quality(
                data, imputed_data, missing_info, column_methods
            )

            # Mark issues as resolved
            for issue in issues:
                result.mark_issue_resolved(issue.id)

            # Calculate execution time
            end_time = datetime.utcnow()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Generate additional recommendations
            result.additional_recommendations = await self._generate_recommendations(
                data, missing_info, missing_pattern, column_methods
            )

        except Exception as e:
            logger.error(f"Imputation failed: {str(e)}")
            result.is_successful = False
            result.add_issue(CleanupIssue(
                issue_type="imputation_error",
                severity=CleanupSeverity.CRITICAL,
                message=f"Imputation failed: {str(e)}",
                field="",
                suggested_action="Review data format and try different imputation method",
                confidence=1.0,
                estimated_impact="Missing data remains unhandled"
            ))

        return result

    async def analyze_data(self, data: pd.DataFrame, context: Optional[CleanupContext] = None) -> List[CleanupIssue]:
        """Analyze data to identify missing data patterns without imputing."""
        missing_info = await self._identify_missing_data(data)
        if not missing_info:
            return []

        issues = await self._create_missing_data_issues(data, missing_info)
        return issues

    async def _analyze_missing_patterns(self, data: pd.DataFrame) -> MissingDataPattern:
        """Analyze the pattern of missing data."""
        missing_data = data.isnull()

        # Calculate missing percentage
        missing_percentage = (missing_data.sum() / len(data)) * 100

        # Check for systematic patterns
        if self._has_systematic_pattern(missing_data):
            return MissingDataPattern.SYSTEMATIC

        # Check correlation between missing indicators
        if len(data.columns) > 1:
            missing_corr = missing_data.corr()

            # If missing values are highly correlated, likely MAR or MNAR
            high_correlations = (missing_corr > 0.7).sum().sum() - len(data.columns)  # Subtract diagonal
            if high_correlations > 0:
                return MissingDataPattern.MAR

        # Default to MCAR if no clear pattern
        return MissingDataPattern.MCAR

    def _has_systematic_pattern(self, missing_data: pd.DataFrame) -> bool:
        """Check if missing data follows a systematic pattern."""
        # Check for patterns like missing data in blocks or specific sequences
        for column in missing_data.columns:
            missing_series = missing_data[column]

            # Check for consecutive missing blocks
            changes = missing_series.diff().abs().sum()
            total_missing = missing_series.sum()

            if total_missing > 0:
                # If very few changes relative to missing count, likely systematic
                change_ratio = changes / total_missing
                if change_ratio < 0.1:  # Less than 10% changes
                    return True

        return False

    async def _identify_missing_data(self, data: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Identify columns with missing data and analyze patterns."""
        if columns is None:
            columns = data.columns.tolist()

        missing_info = {}

        for column in columns:
            missing_count = data[column].isnull().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / len(data)) * 100

                missing_info[column] = {
                    'missing_count': missing_count,
                    'missing_percentage': missing_percentage,
                    'data_type': str(data[column].dtype),
                    'total_values': len(data),
                    'non_missing_values': len(data) - missing_count,
                    'missing_indices': data[data[column].isnull()].index.tolist()
                }

        return missing_info

    async def _create_missing_data_issues(self, data: pd.DataFrame, missing_info: Dict[str, Dict[str, Any]]) -> List[CleanupIssue]:
        """Create CleanupIssue objects for missing data."""
        issues = []

        for column, info in missing_info.items():
            # Determine severity based on missing percentage
            severity = self._determine_missing_data_severity(info['missing_percentage'])

            # Suggest appropriate imputation method
            suggested_method = self._suggest_imputation_method(data[column])

            issue = CleanupIssue(
                issue_type="missing_data",
                severity=severity,
                message=f"Column '{column}' has {info['missing_count']} missing values ({info['missing_percentage']:.1f}%)",
                field=column,
                row_indices=info['missing_indices'],
                affected_values=[],  # Don't store null values
                suggested_action=f"Impute missing values using {suggested_method.value} method",
                confidence=0.8,  # High confidence in detecting missing data
                estimated_impact=f"Affects {info['missing_count']} rows ({info['missing_percentage']:.1f}% of data)",
                metadata={
                    "missing_count": info['missing_count'],
                    "missing_percentage": info['missing_percentage'],
                    "data_type": info['data_type'],
                    "suggested_method": suggested_method.value
                }
            )
            issues.append(issue)

        return issues

    def _determine_missing_data_severity(self, missing_percentage: float) -> CleanupSeverity:
        """Determine severity based on percentage of missing data."""
        if missing_percentage >= 50:
            return CleanupSeverity.CRITICAL
        elif missing_percentage >= 25:
            return CleanupSeverity.HIGH
        elif missing_percentage >= 10:
            return CleanupSeverity.MEDIUM
        elif missing_percentage >= 5:
            return CleanupSeverity.LOW
        else:
            return CleanupSeverity.INFO

    def _suggest_imputation_method(self, series: pd.Series) -> ImputationMethod:
        """Suggest appropriate imputation method based on data type and distribution."""
        # Remove missing values for analysis
        non_missing = series.dropna()

        if len(non_missing) == 0:
            return ImputationMethod.DROP

        # Numeric data
        if pd.api.types.is_numeric_dtype(series):
            # Check distribution
            if len(non_missing.unique()) <= 10:  # Discrete numeric
                return ImputationMethod.MODE
            else:  # Continuous numeric
                # Use median for skewed data, mean for normal data
                try:
                    if pd.api.types.is_datetime64_any_dtype(non_missing):
                        return ImputationMethod.FORWARD_FILL
                    skew_val = non_missing.skew()
                    if not isinstance(skew_val, (int, float)) or pd.isna(skew_val):
                        return ImputationMethod.MEDIAN
                    skewness = float(skew_val)
                    if abs(skewness) > 1:  # Highly skewed
                        return ImputationMethod.MEDIAN
                    else:
                        return ImputationMethod.MEAN
                except (TypeError, ValueError, AttributeError, OverflowError):
                    return ImputationMethod.MEDIAN

        # Categorical data
        elif pd.api.types.is_string_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
            return ImputationMethod.MODE

        # DateTime data
        elif pd.api.types.is_datetime64_any_dtype(series):
            return ImputationMethod.FORWARD_FILL

        # Default
        return ImputationMethod.MEDIAN

    async def _determine_imputation_methods(self, data: pd.DataFrame, missing_info: Dict[str, Dict[str, Any]],
                                          strategy: ImputationStrategy, default_method: ImputationMethod) -> Dict[str, str]:
        """Determine the best imputation method for each column."""
        column_methods = {}

        for column, info in missing_info.items():
            if strategy == ImputationStrategy.AUTOMATIC:
                # Automatically choose based on data characteristics
                method = self._suggest_imputation_method(data[column])

            elif strategy == ImputationStrategy.CONSERVATIVE:
                # Use simple, safe methods
                if pd.api.types.is_numeric_dtype(data[column]):
                    method = ImputationMethod.MEDIAN
                else:
                    method = ImputationMethod.MODE

            elif strategy == ImputationStrategy.AGGRESSIVE:
                # Use advanced methods for better accuracy
                if info['missing_percentage'] > 20:
                    method = ImputationMethod.ITERATIVE
                else:
                    method = ImputationMethod.KNN

            else:  # Use default method
                method = default_method

            column_methods[column] = method.value

        return column_methods

    async def _perform_imputation(self, data: pd.DataFrame, missing_info: Dict[str, Dict[str, Any]],
                                column_methods: Dict[str, str], fill_value: Optional[Any] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Perform the actual imputation based on determined methods."""
        imputed_data = data.copy()
        total_imputed = 0
        columns_imputed = []
        rows_affected = set()

        for column, method_name in column_methods.items():
            method = ImputationMethod(method_name)
            original_missing_count = imputed_data[column].isnull().sum()

            if original_missing_count == 0:
                continue

            try:
                if method == ImputationMethod.MEAN:
                    fill_val = imputed_data[column].mean()
                    imputed_data[column].fillna(fill_val, inplace=True)

                elif method == ImputationMethod.MEDIAN:
                    fill_val = imputed_data[column].median()
                    imputed_data[column].fillna(fill_val, inplace=True)

                elif method == ImputationMethod.MODE:
                    mode_values = imputed_data[column].mode()
                    if len(mode_values) > 0:
                        fill_val = mode_values.iloc[0]
                        imputed_data[column].fillna(fill_val, inplace=True)

                elif method == ImputationMethod.FORWARD_FILL:
                    imputed_data[column] = imputed_data[column].ffill()

                elif method == ImputationMethod.BACKWARD_FILL:
                    imputed_data[column] = imputed_data[column].bfill()

                elif method == ImputationMethod.LINEAR_INTERPOLATION:
                    if pd.api.types.is_numeric_dtype(imputed_data[column]):
                        imputed_data[column].interpolate(method='linear', inplace=True)

                elif method == ImputationMethod.KNN:
                    await self._apply_knn_imputation(imputed_data, [column])

                elif method == ImputationMethod.ITERATIVE:
                    await self._apply_iterative_imputation(imputed_data, [column])

                elif method == ImputationMethod.CONSTANT:
                    if fill_value is not None:
                        imputed_data[column].fillna(fill_value, inplace=True)

                elif method == ImputationMethod.DROP:
                    # Drop rows with missing values in this column
                    missing_rows = imputed_data[imputed_data[column].isnull()].index
                    imputed_data = imputed_data.drop(missing_rows)

                # Calculate imputation statistics
                new_missing_count = imputed_data[column].isnull().sum()
                values_imputed = original_missing_count - new_missing_count

                if values_imputed > 0:
                    total_imputed += values_imputed
                    columns_imputed.append(column)
                    # Add affected rows
                    affected_indices = missing_info[column]['missing_indices']
                    rows_affected.update(affected_indices)

            except Exception as e:
                logger.warning(f"Imputation failed for column {column} with method {method}: {str(e)}")
                # Fallback to median/mode
                if pd.api.types.is_numeric_dtype(imputed_data[column]):
                    fill_val = imputed_data[column].median()
                else:
                    mode_values = imputed_data[column].mode()
                    fill_val = mode_values.iloc[0] if len(mode_values) > 0 else "Unknown"

                imputed_data[column].fillna(fill_val, inplace=True)

        stats = {
            'total_imputed': total_imputed,
            'columns_imputed': columns_imputed,
            'rows_affected': len(rows_affected)
        }

        return imputed_data, stats

    async def _apply_knn_imputation(self, data: pd.DataFrame, columns: List[str]):
        """Apply KNN imputation to specified columns."""
        try:
            # Prepare data for KNN imputation
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()

            if len(numeric_columns) < 2:
                # Not enough numeric columns for KNN, fallback to median
                for column in columns:
                    if column in numeric_columns:
                        data[column].fillna(data[column].median(), inplace=True)
                return

            # Apply KNN imputation
            imputer = KNNImputer(n_neighbors=5)
            imputed_values = imputer.fit_transform(data[numeric_columns])

            # Update specified columns
            for i, column in enumerate(numeric_columns):
                if column in columns:
                    data[column] = imputed_values[:, i]

        except Exception as e:
            logger.warning(f"KNN imputation failed: {str(e)}")
            # Fallback to median imputation
            for column in columns:
                if pd.api.types.is_numeric_dtype(data[column]):
                    data[column].fillna(data[column].median(), inplace=True)

    async def _apply_iterative_imputation(self, data: pd.DataFrame, columns: List[str]):
        """Apply iterative imputation (MICE) to specified columns."""
        try:
            # Prepare data for iterative imputation
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()

            if len(numeric_columns) < 2:
                # Not enough numeric columns for iterative imputation
                for column in columns:
                    if column in numeric_columns:
                        data[column].fillna(data[column].median(), inplace=True)
                return

            # Apply iterative imputation
            imputer = IterativeImputer(random_state=42, max_iter=10)
            imputed_values = imputer.fit_transform(data[numeric_columns])

            # Ensure dense array for indexing
            imputed_array = np.asarray(imputed_values)

            # Update specified columns
            for i, column in enumerate(numeric_columns):
                if column in columns:
                    data[column] = imputed_array[:, i]

        except Exception as e:
            logger.warning(f"Iterative imputation failed: {str(e)}")
            # Fallback to median imputation
            for column in columns:
                if pd.api.types.is_numeric_dtype(data[column]):
                    data[column].fillna(data[column].median(), inplace=True)

    async def _calculate_imputation_quality(self, original_data: pd.DataFrame, imputed_data: pd.DataFrame,
                                          missing_info: Dict[str, Dict[str, Any]], column_methods: Dict[str, str]) -> float:
        """Calculate quality score for the imputation results."""
        quality_scores = []

        for column, info in missing_info.items():
            if column not in column_methods:
                continue

            method = ImputationMethod(column_methods[column])

            # Base quality score based on method sophistication
            method_quality = {
                ImputationMethod.MEAN: 0.6,
                ImputationMethod.MEDIAN: 0.7,
                ImputationMethod.MODE: 0.7,
                ImputationMethod.FORWARD_FILL: 0.5,
                ImputationMethod.BACKWARD_FILL: 0.5,
                ImputationMethod.LINEAR_INTERPOLATION: 0.8,
                ImputationMethod.KNN: 0.9,
                ImputationMethod.ITERATIVE: 0.95,
                ImputationMethod.CONSTANT: 0.4,
                ImputationMethod.DROP: 0.3
            }.get(method, 0.5)

            # Adjust based on missing percentage (less missing = higher quality)
            missing_penalty = info['missing_percentage'] / 100  # 0-1
            adjusted_quality = method_quality * (1 - missing_penalty * 0.5)  # Reduce by up to 50%

            quality_scores.append(adjusted_quality)

        return float(np.mean(quality_scores)) if quality_scores else 0.0

    async def _generate_recommendations(self, data: pd.DataFrame, missing_info: Dict[str, Dict[str, Any]],
                                      missing_pattern: MissingDataPattern, column_methods: Dict[str, str]) -> List[str]:
        """Generate additional recommendations based on imputation analysis."""
        recommendations = []

        total_missing_percentage = sum(info['missing_percentage'] for info in missing_info.values()) / len(missing_info)

        if total_missing_percentage > 30:
            recommendations.append("High levels of missing data detected. Consider reviewing data collection processes.")

        if missing_pattern == MissingDataPattern.SYSTEMATIC:
            recommendations.append("Systematic missing data pattern detected. Investigate the root cause of missing data.")

        # Method-specific recommendations
        iterative_columns = [col for col, method in column_methods.items() if method == ImputationMethod.ITERATIVE.value]
        if iterative_columns:
            recommendations.append(f"Iterative imputation used for {len(iterative_columns)} columns. Validate results carefully.")

        drop_columns = [col for col, method in column_methods.items() if method == ImputationMethod.DROP.value]
        if drop_columns:
            recommendations.append(f"Rows dropped for {len(drop_columns)} columns. Consider if data loss is acceptable.")

        return recommendations

    def get_cleanup_info(self) -> Dict[str, Any]:
        """Get information about the imputation engine."""
        return {
            "name": "ImputationEngine",
            "version": "1.0.0",
            "description": "Comprehensive missing data imputation system",
            "supported_methods": [method.value for method in self.supported_methods],
            "supported_strategies": [strategy.value for strategy in self.supported_strategies],
            "capabilities": [
                "Statistical imputation",
                "Machine learning imputation",
                "Pattern-aware imputation",
                "Quality assessment",
                "Automatic method selection"
            ]
        }
