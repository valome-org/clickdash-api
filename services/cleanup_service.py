"""
Unified cleanup service that coordinates all data cleanup operations.

This service provides a single interface for all cleanup functionality including:
- Automated outlier handling
- Smart duplicate resolution
- Missing data imputation
- Data transformation recommendations
- Comprehensive cleanup reporting
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field
import uuid
import logging

from core.cleanup import (
    OutlierHandler,
    DuplicateResolver,
    ImputationEngine,
    TransformationRecommender,
    CleanupResult,
    CleanupIssue,
    CleanupSeverity,
    CleanupContext,
    CleanupStrategy,
    OutlierDetectionMethod,
    OutlierHandlingStrategy,
    DuplicateDetectionType,
    DuplicateResolutionStrategy,
    ImputationMethod,
    ImputationStrategy,
    TransformationType
)

logger = logging.getLogger(__name__)


class CleanupRequest(BaseModel):
    """Request for comprehensive data cleanup."""

    data: Optional[Any] = Field(None, description="Data to clean (will be converted to DataFrame)")
    cleanup_types: List[str] = Field(default_factory=lambda: ["outliers", "duplicates", "missing", "transformations"],
                                   description="Types of cleanup to perform")

    # Cleanup preferences
    strategy: CleanupStrategy = Field(default=CleanupStrategy.SUGGEST, description="Overall cleanup strategy")
    aggressiveness: float = Field(default=0.5, description="Cleanup aggressiveness level (0-1)")
    preserve_original: bool = Field(default=True, description="Whether to preserve original data")

    # Specific method preferences
    outlier_method: Optional[OutlierDetectionMethod] = Field(None, description="Preferred outlier detection method")
    outlier_strategy: Optional[OutlierHandlingStrategy] = Field(None, description="Preferred outlier handling strategy")
    duplicate_detection: Optional[DuplicateDetectionType] = Field(None, description="Preferred duplicate detection type")
    duplicate_strategy: Optional[DuplicateResolutionStrategy] = Field(None, description="Preferred duplicate resolution strategy")
    imputation_method: Optional[ImputationMethod] = Field(None, description="Preferred imputation method")
    imputation_strategy: Optional[ImputationStrategy] = Field(None, description="Preferred imputation strategy")

    # Constraints and options
    target_columns: Optional[List[str]] = Field(None, description="Specific columns to focus on")
    context: Optional[Dict[str, Any]] = Field(None, description="Cleanup context")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional cleanup options")


class CleanupReport(BaseModel):
    """Comprehensive cleanup report combining all cleanup results."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Report ID")
    dataset_name: str = Field(..., description="Name of cleaned dataset")
    cleanup_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When cleanup was performed")

    # Overall results
    overall_successful: bool = Field(..., description="Overall cleanup status")
    total_issues: int = Field(default=0, description="Total number of issues found")
    total_resolved: int = Field(default=0, description="Total number of issues resolved")
    severity_summary: Dict[str, int] = Field(default_factory=dict, description="Issue count by severity")

    # Individual cleanup results
    outlier_results: Optional[CleanupResult] = Field(None, description="Outlier handling results")
    duplicate_results: Optional[CleanupResult] = Field(None, description="Duplicate resolution results")
    imputation_results: Optional[CleanupResult] = Field(None, description="Missing data imputation results")
    transformation_results: Optional[CleanupResult] = Field(None, description="Data transformation results")

    # Aggregated insights
    data_quality_improvement: float = Field(default=0.0, description="Overall data quality improvement score")
    performance_improvement: float = Field(default=0.0, description="Estimated performance improvement")
    recommendations: List[str] = Field(default_factory=list, description="Consolidated recommendations")

    # Performance metrics
    total_execution_time_ms: float = Field(default=0.0, description="Total cleanup time")
    cleanup_performance: Dict[str, float] = Field(default_factory=dict, description="Performance by cleanup type")

    # Data changes summary
    rows_before: int = Field(default=0, description="Number of rows before cleanup")
    rows_after: int = Field(default=0, description="Number of rows after cleanup")
    columns_before: int = Field(default=0, description="Number of columns before cleanup")
    columns_after: int = Field(default=0, description="Number of columns after cleanup")


class CleanupService:
    """Unified cleanup service coordinating all cleanup operations."""

    def __init__(self):
        # Initialize cleanup handlers
        self.outlier_handler = OutlierHandler()
        self.duplicate_resolver = DuplicateResolver()
        self.imputation_engine = ImputationEngine()
        self.transformation_recommender = TransformationRecommender()

        # Cleanup history
        self.cleanup_history: List[CleanupReport] = []

    async def cleanup_comprehensive(self, request: CleanupRequest) -> CleanupReport:
        """
        Perform comprehensive data cleanup using all available handlers.

        Args:
            request: Cleanup request with data and preferences

        Returns:
            Comprehensive cleanup report
        """
        start_time = datetime.utcnow()

        # Convert data to DataFrame if needed
        try:
            if isinstance(request.data, pd.DataFrame):
                data = request.data.copy()
            else:
                # Handle other data formats (dict, list, etc.)
                if request.data is None:
                    data = pd.DataFrame()
                else:
                    data = pd.DataFrame(request.data)

            # Validate DataFrame
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Data is not a valid DataFrame")

            logger.info(f"Data loaded successfully: {len(data)} rows, {len(data.columns)} columns")

        except Exception as e:
            logger.error(f"Failed to convert data to DataFrame: {str(e)}")
            data = pd.DataFrame()

        # Store original dimensions
        try:
            if hasattr(data, 'shape'):
                original_rows, original_cols = data.shape
            else:
                original_rows, original_cols = 0, 0
        except Exception as e:
            logger.error(f"Failed to get DataFrame shape: {str(e)}")
            original_rows, original_cols = 0, 0

        # Initialize report
        report = CleanupReport(
            dataset_name=request.options.get('dataset_name', 'unknown'),
            overall_successful=True,
            rows_before=original_rows,
            columns_before=original_cols,
            outlier_results=None,
            duplicate_results=None,
            imputation_results=None,
            transformation_results=None
        )

        # Create cleanup context
        context = CleanupContext(
            dataset_name=request.options.get('dataset_name', 'unknown'),
            cleanup_strategy=request.strategy,
            aggressiveness_level=request.aggressiveness,
            preserve_original=request.preserve_original,
            **(request.context or {})
        )

        # Current working data
        try:
            current_data = data.copy()
        except Exception as e:
            logger.error(f"Failed to copy data: {str(e)}")
            current_data = pd.DataFrame()

        try:
            # Perform cleanup operations in order
            if "outliers" in request.cleanup_types:
                report.outlier_results, current_data = await self._handle_outliers(
                    current_data, request, context
                )
                if report.outlier_results:
                    report.cleanup_performance["outliers"] = report.outlier_results.execution_time_ms

            if "duplicates" in request.cleanup_types:
                report.duplicate_results, current_data = await self._resolve_duplicates(
                    current_data, request, context
                )
                if report.duplicate_results:
                    report.cleanup_performance["duplicates"] = report.duplicate_results.execution_time_ms

            if "missing" in request.cleanup_types:
                report.imputation_results, current_data = await self._impute_missing_data(
                    current_data, request, context
                )
                if report.imputation_results:
                    report.cleanup_performance["missing"] = report.imputation_results.execution_time_ms

            if "transformations" in request.cleanup_types:
                report.transformation_results, current_data = await self._recommend_transformations(
                    current_data, request, context
                )
                if report.transformation_results:
                    report.cleanup_performance["transformations"] = report.transformation_results.execution_time_ms

            # Update final dimensions
            try:
                if hasattr(current_data, 'shape'):
                    report.rows_after, report.columns_after = current_data.shape
                else:
                    report.rows_after, report.columns_after = 0, 0
            except Exception as e:
                logger.error(f"Failed to get final DataFrame shape: {str(e)}")
                report.rows_after, report.columns_after = 0, 0

            # Calculate overall metrics
            await self._calculate_overall_metrics(report, data, current_data)

            # Generate consolidated recommendations
            await self._generate_consolidated_recommendations(report)

        except Exception as e:
            logger.error(f"Comprehensive cleanup failed: {str(e)}")
            report.overall_successful = False

        # Calculate total execution time
        end_time = datetime.utcnow()
        report.total_execution_time_ms = (end_time - start_time).total_seconds() * 1000

        # Store in history
        self.cleanup_history.append(report)

        return report

    async def _handle_outliers(self, data: pd.DataFrame, request: CleanupRequest,
                             context: CleanupContext) -> tuple[Optional[CleanupResult], pd.DataFrame]:
        """Handle outliers in the data."""
        try:
            kwargs = {
                'method': request.outlier_method or OutlierDetectionMethod.IQR,
                'strategy': request.outlier_strategy or OutlierHandlingStrategy.FLAG_ONLY,
                'columns': request.target_columns
            }

            # Use more aggressive strategy based on context
            if context.cleanup_strategy == CleanupStrategy.AUTOMATIC:
                kwargs['strategy'] = OutlierHandlingStrategy.CAP

            result = await self.outlier_handler.clean(data, context, **kwargs)

            if result.is_successful and result.cleaned_data is not None and isinstance(result.cleaned_data, pd.DataFrame):
                return result, result.cleaned_data
            else:
                return result, data

        except Exception as e:
            logger.error(f"Outlier handling failed: {str(e)}")
            return None, data

    async def _resolve_duplicates(self, data: pd.DataFrame, request: CleanupRequest,
                                context: CleanupContext) -> tuple[Optional[CleanupResult], pd.DataFrame]:
        """Resolve duplicates in the data."""
        try:
            kwargs = {
                'detection_type': request.duplicate_detection or DuplicateDetectionType.EXACT,
                'strategy': request.duplicate_strategy or DuplicateResolutionStrategy.FLAG_ONLY,
                'columns': request.target_columns
            }

            # Use more aggressive strategy based on context
            if context.cleanup_strategy == CleanupStrategy.AUTOMATIC:
                kwargs['strategy'] = DuplicateResolutionStrategy.KEEP_FIRST

            result = await self.duplicate_resolver.clean(data, context, **kwargs)

            if result.is_successful and result.cleaned_data is not None and isinstance(result.cleaned_data, pd.DataFrame):
                return result, result.cleaned_data
            else:
                return result, data

        except Exception as e:
            logger.error(f"Duplicate resolution failed: {str(e)}")
            return None, data

    async def _impute_missing_data(self, data: pd.DataFrame, request: CleanupRequest,
                                 context: CleanupContext) -> tuple[Optional[CleanupResult], pd.DataFrame]:
        """Impute missing data."""
        try:
            kwargs = {
                'method': request.imputation_method or ImputationMethod.MEDIAN,
                'strategy': request.imputation_strategy or ImputationStrategy.AUTOMATIC,
                'columns': request.target_columns
            }

            result = await self.imputation_engine.clean(data, context, **kwargs)

            if result.is_successful and result.cleaned_data is not None and isinstance(result.cleaned_data, pd.DataFrame):
                return result, result.cleaned_data
            else:
                return result, data

        except Exception as e:
            logger.error(f"Missing data imputation failed: {str(e)}")
            return None, data

    async def _recommend_transformations(self, data: pd.DataFrame, request: CleanupRequest,
                                       context: CleanupContext) -> tuple[Optional[CleanupResult], pd.DataFrame]:
        """Generate and optionally apply transformation recommendations."""
        try:
            kwargs = {
                'apply_transformations': context.cleanup_strategy == CleanupStrategy.AUTOMATIC,
                'transformation_types': None  # Analyze all types
            }

            result = await self.transformation_recommender.clean(data, context, **kwargs)

            if result.is_successful and result.cleaned_data is not None and isinstance(result.cleaned_data, pd.DataFrame):
                return result, result.cleaned_data
            else:
                return result, data

        except Exception as e:
            logger.error(f"Transformation recommendations failed: {str(e)}")
            return None, data

    async def _calculate_overall_metrics(self, report: CleanupReport, original_data: pd.DataFrame,
                                       cleaned_data: pd.DataFrame):
        """Calculate overall cleanup metrics."""
        all_issues = []
        all_resolved = []

        # Collect all issues and resolved counts
        for result in [report.outlier_results, report.duplicate_results,
                      report.imputation_results, report.transformation_results]:
            if result:
                all_issues.extend(result.issues_found)
                all_resolved.extend(result.issues_resolved)

        # Count issues by severity
        severity_counts = {severity.value: 0 for severity in CleanupSeverity}
        for issue in all_issues:
            severity_counts[issue.severity.value] += 1

        report.total_issues = len(all_issues)
        report.total_resolved = len(all_resolved)
        report.severity_summary = severity_counts

        # Calculate data quality improvement
        report.data_quality_improvement = await self._calculate_quality_improvement(
            original_data, cleaned_data, report
        )

        # Calculate performance improvement
        report.performance_improvement = await self._calculate_performance_improvement(
            original_data, cleaned_data
        )

    async def _calculate_quality_improvement(self, original_data: pd.DataFrame,
                                           cleaned_data: pd.DataFrame, report: CleanupReport) -> float:
        """Calculate overall data quality improvement score."""
        improvements = []

        # Improvement from issue resolution
        if report.total_issues > 0:
            resolution_rate = report.total_resolved / report.total_issues
            improvements.append(resolution_rate * 30)  # Up to 30 points

        # Improvement from specific operations
        if report.outlier_results:
            outliers_handled = getattr(report.outlier_results, 'outliers_handled', 0)
            outlier_improvement = min(20, outliers_handled * 2)
            improvements.append(outlier_improvement)

        if report.duplicate_results:
            duplicates_resolved = getattr(report.duplicate_results, 'duplicates_resolved', 0)
            duplicate_improvement = min(15, duplicates_resolved * 1.5)
            improvements.append(duplicate_improvement)

        if report.imputation_results:
            values_imputed = getattr(report.imputation_results, 'values_imputed', 0)
            imputation_improvement = min(25, values_imputed * 0.1)
            improvements.append(imputation_improvement)

        if report.transformation_results:
            transformations_applied = getattr(report.transformation_results, 'transformations_applied', 0)
            transformation_improvement = min(10, transformations_applied * 5)
            improvements.append(transformation_improvement)

        return sum(improvements)

    async def _calculate_performance_improvement(self, original_data: pd.DataFrame,
                                               cleaned_data: pd.DataFrame) -> float:
        """Calculate estimated performance improvement."""
        improvements = []

        try:
            # Memory improvement from data type optimizations
            original_memory = original_data.memory_usage(deep=True).sum()
            cleaned_memory = cleaned_data.memory_usage(deep=True).sum()

            if original_memory > 0:
                memory_improvement = ((original_memory - cleaned_memory) / original_memory) * 100
                improvements.append(max(0, memory_improvement))

            # Row reduction improvement
            if len(original_data) > 0:
                row_reduction = ((len(original_data) - len(cleaned_data)) / len(original_data)) * 100
                improvements.append(max(0, row_reduction * 0.5))  # Half weight for row reduction
        except Exception as e:
            logger.error(f"Failed to calculate performance improvement: {str(e)}")

        return sum(improvements)

    async def _generate_consolidated_recommendations(self, report: CleanupReport):
        """Generate consolidated recommendations from all cleanup results."""
        recommendations = set()

        # Collect recommendations from all cleanup operations
        for result in [report.outlier_results, report.duplicate_results,
                      report.imputation_results, report.transformation_results]:
            if result and result.additional_recommendations:
                recommendations.update(result.additional_recommendations)

        # Add overall recommendations based on results
        if report.data_quality_improvement > 50:
            recommendations.add("Significant data quality improvement achieved. Consider implementing similar cleanup in your data pipeline.")
        elif report.data_quality_improvement > 20:
            recommendations.add("Good data quality improvement achieved. Review and apply additional suggested transformations.")
        elif report.data_quality_improvement < 10:
            recommendations.add("Limited data quality improvement. Data may already be well-structured or require domain-specific cleanup.")

        # Performance recommendations
        if report.performance_improvement > 20:
            recommendations.add("Substantial performance improvements achieved through data optimization.")

        # Issue-based recommendations
        critical_issues = report.severity_summary.get(CleanupSeverity.CRITICAL.value, 0)
        if critical_issues > 0:
            recommendations.add(f"{critical_issues} critical issues remain. These should be addressed manually or with specialized tools.")

        report.recommendations = list(recommendations)

    # Service information and analytics methods

    def get_cleanup_analytics(self) -> Dict[str, Any]:
        """Get analytics from cleanup history."""
        if not self.cleanup_history:
            return {}

        total_cleanups = len(self.cleanup_history)
        avg_quality_improvement = sum(r.data_quality_improvement for r in self.cleanup_history) / total_cleanups
        avg_execution_time = sum(r.total_execution_time_ms for r in self.cleanup_history) / total_cleanups

        # Most common cleanup types
        cleanup_type_counts = {}
        for report in self.cleanup_history:
            for cleanup_type in report.cleanup_performance.keys():
                cleanup_type_counts[cleanup_type] = cleanup_type_counts.get(cleanup_type, 0) + 1

        return {
            "total_cleanups": total_cleanups,
            "average_quality_improvement": round(avg_quality_improvement, 2),
            "average_execution_time_ms": round(avg_execution_time, 2),
            "most_used_cleanup_types": sorted(cleanup_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    def get_cleanup_history(self, limit: Optional[int] = None) -> List[CleanupReport]:
        """Get cleanup history."""
        if limit:
            return self.cleanup_history[-limit:]
        return self.cleanup_history

    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the cleanup service."""
        return {
            "name": "CleanupService",
            "version": "1.0.0",
            "description": "Unified data cleanup service with outlier handling, duplicate resolution, imputation, and transformations",
            "components": {
                "outlier_handler": self.outlier_handler.get_cleanup_info(),
                "duplicate_resolver": self.duplicate_resolver.get_cleanup_info(),
                "imputation_engine": self.imputation_engine.get_cleanup_info(),
                "transformation_recommender": self.transformation_recommender.get_cleanup_info()
            },
            "supported_cleanup_types": ["outliers", "duplicates", "missing", "transformations"],
            "supported_strategies": [strategy.value for strategy in CleanupStrategy],
            "cleanup_history_count": len(self.cleanup_history)
        }


# Global service instance
cleanup_service = CleanupService()
