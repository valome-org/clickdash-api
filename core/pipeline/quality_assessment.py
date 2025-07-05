"""
Data Quality Assessment Pipeline - Comprehensive data quality evaluation
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import pandas as pd
import numpy as np
from enum import Enum
from pydantic import BaseModel, Field
import logging
from scipy import stats

from .base import PipelineStage, PipelineStageType
from utils.serialization import make_json_serializable

logger = logging.getLogger(__name__)


class QualityIssueType(Enum):
    """Types of data quality issues"""
    MISSING_DATA = "missing_data"
    DUPLICATE_RECORDS = "duplicate_records"
    OUTLIERS = "outliers"
    INCONSISTENT_FORMAT = "inconsistent_format"
    INVALID_VALUES = "invalid_values"
    CONSTRAINT_VIOLATION = "constraint_violation"
    ENCODING_ERROR = "encoding_error"
    TYPE_MISMATCH = "type_mismatch"


class QualityIssueSeverity(Enum):
    """Severity levels for data quality issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class QualityIssue(BaseModel):
    """Individual data quality issue"""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issue_type: QualityIssueType
    severity: QualityIssueSeverity
    column: Optional[str] = None
    row_indices: List[int] = Field(default_factory=list)
    description: str
    recommendation: str
    affected_count: int = 0
    percentage: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            QualityIssueType: lambda v: v.value,
            QualityIssueSeverity: lambda v: v.value
        }


class DataQualityReport(BaseModel):
    """Comprehensive data quality report"""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = Field(default_factory=datetime.now)
    dataset_info: Dict[str, Any] = Field(default_factory=dict)

    # Overall quality metrics
    overall_quality_score: float = 0.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    validity_score: float = 0.0
    uniqueness_score: float = 0.0

    # Issues summary
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0

    # Detailed issues
    issues: List[QualityIssue] = Field(default_factory=list)

    # Column-specific metrics
    column_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataQualityAssessmentStage(PipelineStage):
    """
    Data quality assessment stage that evaluates data quality comprehensively
    """

    def __init__(self,
                 name: str = "data_quality_assessment",
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name, PipelineStageType.VALIDATION, config)
        config = config or {}
        self.missing_threshold = config.get("missing_threshold", 0.1)  # 10% missing data threshold
        self.outlier_method = config.get("outlier_method", "iqr")  # IQR or z-score
        self.outlier_threshold = config.get("outlier_threshold", 3.0)
        self.duplicate_subset = config.get("duplicate_subset", None)
        self.quality_report: Optional[DataQualityReport] = None

    async def validate_inputs(self, data: pd.DataFrame) -> bool:
        """
        Validate inputs before quality assessment
        """
        try:
            return not data.empty and len(data.columns) > 0
        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return False

    async def execute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Execute data quality assessment
        """
        try:
            # Create comprehensive quality report
            self.quality_report = await self._create_quality_report(data)

            # Add quality metadata to DataFrame
            data.attrs['quality_report_id'] = self.quality_report.report_id
            data.attrs['quality_score'] = self.quality_report.overall_quality_score
            data.attrs['quality_assessment_timestamp'] = datetime.now().isoformat()

            # Update metrics
            self.metrics.update({
                'quality_score': self.quality_report.overall_quality_score,
                'total_issues': self.quality_report.total_issues,
                'critical_issues': self.quality_report.critical_issues,
                'report_id': self.quality_report.report_id,
                'completeness_score': self.quality_report.completeness_score,
                'consistency_score': self.quality_report.consistency_score
            })

            return data

        except Exception as e:
            logger.error(f"Data quality assessment failed: {str(e)}")
            raise

    async def _create_quality_report(self, df: pd.DataFrame) -> DataQualityReport:
        """
        Create comprehensive data quality report
        """
        try:
            issues = []

            # Assess missing data
            missing_issues = await self._assess_missing_data(df)
            issues.extend(missing_issues)

            # Assess duplicate records
            duplicate_issues = await self._assess_duplicate_records(df)
            issues.extend(duplicate_issues)

            # Assess outliers
            outlier_issues = await self._assess_outliers(df)
            issues.extend(outlier_issues)

            # Assess data consistency
            consistency_issues = await self._assess_data_consistency(df)
            issues.extend(consistency_issues)

            # Assess data validity
            validity_issues = await self._assess_data_validity(df)
            issues.extend(validity_issues)

            # Calculate quality scores
            completeness_score = await self._calculate_completeness_score(df)
            consistency_score = await self._calculate_consistency_score(df)
            validity_score = await self._calculate_validity_score(df)
            uniqueness_score = await self._calculate_uniqueness_score(df)

            # Calculate overall quality score
            overall_quality_score = (
                completeness_score * 0.3 +
                consistency_score * 0.25 +
                validity_score * 0.25 +
                uniqueness_score * 0.2
            )

            # Count issues by severity
            severity_counts = {
                QualityIssueSeverity.CRITICAL: 0,
                QualityIssueSeverity.HIGH: 0,
                QualityIssueSeverity.MEDIUM: 0,
                QualityIssueSeverity.LOW: 0
            }

            for issue in issues:
                severity_counts[issue.severity] += 1

            # Generate column metrics
            column_metrics = await self._generate_column_metrics(df)

            # Generate recommendations
            recommendations = await self._generate_recommendations(issues, df)

            return DataQualityReport(
                dataset_info={
                    'rows': len(df),
                    'columns': len(df.columns),
                    'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
                    'column_names': list(df.columns)
                },
                overall_quality_score=round(overall_quality_score, 2),
                completeness_score=round(completeness_score, 2),
                consistency_score=round(consistency_score, 2),
                validity_score=round(validity_score, 2),
                uniqueness_score=round(uniqueness_score, 2),
                total_issues=len(issues),
                critical_issues=severity_counts[QualityIssueSeverity.CRITICAL],
                high_issues=severity_counts[QualityIssueSeverity.HIGH],
                medium_issues=severity_counts[QualityIssueSeverity.MEDIUM],
                low_issues=severity_counts[QualityIssueSeverity.LOW],
                issues=issues,
                column_metrics=column_metrics,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Quality report creation failed: {str(e)}")
            raise

    async def _assess_missing_data(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Assess missing data issues
        """
        issues = []

        try:
            for col in df.columns:
                missing_count = df[col].isnull().sum()
                if missing_count > 0:
                    missing_percentage = (missing_count / len(df)) * 100

                    # Determine severity
                    if missing_percentage > 50:
                        severity = QualityIssueSeverity.CRITICAL
                    elif missing_percentage > 25:
                        severity = QualityIssueSeverity.HIGH
                    elif missing_percentage > 10:
                        severity = QualityIssueSeverity.MEDIUM
                    else:
                        severity = QualityIssueSeverity.LOW

                    # Get row indices with missing values
                    missing_indices = df[df[col].isnull()].index.tolist()

                    issue = QualityIssue(
                        issue_type=QualityIssueType.MISSING_DATA,
                        severity=severity,
                        column=col,
                        row_indices=missing_indices[:100],  # Limit to first 100 for performance
                        description=f"Column '{col}' has {missing_count} missing values ({missing_percentage:.1f}%)",
                        recommendation=await self._get_missing_data_recommendation(missing_percentage),
                        affected_count=missing_count,
                        percentage=missing_percentage,
                        metadata={
                            'missing_count': missing_count,
                            'total_rows': len(df),
                            'pattern': await self._analyze_missing_pattern(df, col)
                        }
                    )

                    issues.append(issue)

        except Exception as e:
            logger.error(f"Missing data assessment failed: {str(e)}")

        return issues

    async def _assess_duplicate_records(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Assess duplicate record issues
        """
        issues = []

        try:
            # Check for exact duplicates
            if self.duplicate_subset:
                duplicates = df.duplicated(subset=self.duplicate_subset, keep=False)
            else:
                duplicates = df.duplicated(keep=False)

            duplicate_count = duplicates.sum()

            if duplicate_count > 0:
                duplicate_percentage = (duplicate_count / len(df)) * 100

                # Determine severity
                if duplicate_percentage > 20:
                    severity = QualityIssueSeverity.HIGH
                elif duplicate_percentage > 10:
                    severity = QualityIssueSeverity.MEDIUM
                else:
                    severity = QualityIssueSeverity.LOW

                # Get duplicate indices
                duplicate_indices = df[duplicates].index.tolist()

                issue = QualityIssue(
                    issue_type=QualityIssueType.DUPLICATE_RECORDS,
                    severity=severity,
                    row_indices=duplicate_indices[:100],  # Limit for performance
                    description=f"Found {duplicate_count} duplicate records ({duplicate_percentage:.1f}%)",
                    recommendation="Consider removing duplicate records or investigating data source",
                    affected_count=duplicate_count,
                    percentage=duplicate_percentage,
                    metadata={
                        'duplicate_count': duplicate_count,
                        'unique_duplicates': len(df[duplicates].drop_duplicates()),
                        'subset_columns': self.duplicate_subset
                    }
                )

                issues.append(issue)

        except Exception as e:
            logger.error(f"Duplicate records assessment failed: {str(e)}")

        return issues

    async def _assess_outliers(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Assess outlier issues in numeric columns
        """
        issues = []

        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns

            for col in numeric_columns:
                outlier_indices = await self._detect_outliers(df[col])

                if len(outlier_indices) > 0:
                    outlier_percentage = (len(outlier_indices) / len(df)) * 100

                    # Determine severity
                    if outlier_percentage > 10:
                        severity = QualityIssueSeverity.MEDIUM
                    elif outlier_percentage > 5:
                        severity = QualityIssueSeverity.LOW
                    else:
                        severity = QualityIssueSeverity.INFO

                    # Get outlier values and handle NaN values
                    outlier_values = df.loc[outlier_indices[:10], col].tolist()
                    # Convert NaN values to None for JSON serialization
                    outlier_values = [None if pd.isna(val) else val for val in outlier_values]

                    issue = QualityIssue(
                        issue_type=QualityIssueType.OUTLIERS,
                        severity=severity,
                        column=col,
                        row_indices=outlier_indices[:100],  # Limit for performance
                        description=f"Column '{col}' has {len(outlier_indices)} outliers ({outlier_percentage:.1f}%)",
                        recommendation="Review outliers to determine if they are valid data points or errors",
                        affected_count=len(outlier_indices),
                        percentage=outlier_percentage,
                        metadata={
                            'outlier_method': self.outlier_method,
                            'threshold': self.outlier_threshold,
                            'outlier_values': outlier_values
                        }
                    )

                    issues.append(issue)

        except Exception as e:
            logger.error(f"Outlier assessment failed: {str(e)}")

        return issues

    async def _assess_data_consistency(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Assess data consistency issues
        """
        issues = []

        try:
            # Check for inconsistent data types within columns
            for col in df.columns:
                if df[col].dtype == 'object':
                    inconsistencies = await self._check_type_consistency(df[col])

                    if inconsistencies:
                        issue = QualityIssue(
                            issue_type=QualityIssueType.INCONSISTENT_FORMAT,
                            severity=QualityIssueSeverity.MEDIUM,
                            column=col,
                            description=f"Column '{col}' has inconsistent data formats",
                            recommendation="Standardize data formats within the column",
                            affected_count=len(inconsistencies),
                            percentage=(len(inconsistencies) / len(df)) * 100,
                            metadata={
                                'inconsistency_examples': inconsistencies[:10]
                            }
                        )

                        issues.append(issue)

        except Exception as e:
            logger.error(f"Data consistency assessment failed: {str(e)}")

        return issues

    async def _assess_data_validity(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Assess data validity issues
        """
        issues = []

        try:
            # Check for invalid values based on data type
            for col in df.columns:
                invalid_values = await self._check_validity(df[col])

                if invalid_values:
                    issue = QualityIssue(
                        issue_type=QualityIssueType.INVALID_VALUES,
                        severity=QualityIssueSeverity.MEDIUM,
                        column=col,
                        description=f"Column '{col}' has {len(invalid_values)} invalid values",
                        recommendation="Review and correct invalid values",
                        affected_count=len(invalid_values),
                        percentage=(len(invalid_values) / len(df)) * 100,
                        metadata={
                            'invalid_examples': invalid_values[:10]
                        }
                    )

                    issues.append(issue)

        except Exception as e:
            logger.error(f"Data validity assessment failed: {str(e)}")

        return issues

    async def _detect_outliers(self, series: pd.Series) -> List[int]:
        """
        Detect outliers using specified method
        """
        try:
            if self.outlier_method == "iqr":
                return await self._detect_outliers_iqr(series)
            elif self.outlier_method == "zscore":
                return await self._detect_outliers_zscore(series)
            else:
                return []
        except Exception as e:
            logger.error(f"Outlier detection failed: {str(e)}")
            return []

    async def _detect_outliers_iqr(self, series: pd.Series) -> List[int]:
        """
        Detect outliers using IQR method
        """
        # Skip if series is empty or all NaN
        clean_series = series.dropna()
        if len(clean_series) <= 1:
            return []

        Q1 = clean_series.quantile(0.25)
        Q3 = clean_series.quantile(0.75)

        # Check for NaN values in quantiles
        if pd.isna(Q1) or pd.isna(Q3):
            return []

        IQR = Q3 - Q1

        # If IQR is 0 (all values are the same), no outliers
        if IQR == 0:
            return []

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = series[(series < lower_bound) | (series > upper_bound)]
        return outliers.index.tolist()

    async def _detect_outliers_zscore(self, series: pd.Series) -> List[int]:
        """
        Detect outliers using Z-score method
        """
        clean_series = series.dropna()
        mean = clean_series.mean()
        std = clean_series.std()

        if std == 0:
            return []

        z_scores = np.abs((clean_series - mean) / std)
        outlier_mask = z_scores > self.outlier_threshold
        return clean_series[outlier_mask].index.tolist()

    async def _check_type_consistency(self, series: pd.Series) -> List[Any]:
        """
        Check for type consistency within a column
        """
        inconsistencies = []

        try:
            # Sample values to check
            sample_values = series.dropna().head(1000)

            # Try to determine primary type
            numeric_count = 0
            date_count = 0

            for value in sample_values:
                try:
                    float(value)
                    numeric_count += 1
                except:
                    try:
                        pd.to_datetime(value)
                        date_count += 1
                    except:
                        pass

            # If mixed types detected
            if numeric_count > 0 and numeric_count < len(sample_values) * 0.9:
                inconsistencies.extend(sample_values[~sample_values.apply(lambda x: self._is_numeric(x))].tolist())

        except Exception as e:
            logger.error(f"Type consistency check failed: {str(e)}")

        return inconsistencies

    async def _check_validity(self, series: pd.Series) -> List[Any]:
        """
        Check for invalid values based on data type
        """
        invalid_values = []

        try:
            # Check for common invalid patterns
            for value in series.dropna().head(1000):
                if isinstance(value, str):
                    # Check for common invalid strings
                    if value.lower() in ['null', 'none', 'n/a', 'nan', '', ' ']:
                        invalid_values.append(value)
                elif isinstance(value, (int, float)):
                    # Check for invalid numeric values
                    if np.isnan(value) or np.isinf(value):
                        invalid_values.append(value)

        except Exception as e:
            logger.error(f"Validity check failed: {str(e)}")

        return invalid_values

    def _is_numeric(self, value) -> bool:
        """Check if value is numeric"""
        try:
            float(value)
            return True
        except:
            return False

    async def _analyze_missing_pattern(self, df: pd.DataFrame, column: str) -> str:
        """
        Analyze missing data pattern
        """
        try:
            missing_mask = df[column].isnull()

            if missing_mask.sum() == 0:
                return "no_missing"
            elif missing_mask.all():
                return "completely_missing"
            else:
                # Check if missing values are clustered
                missing_diff = missing_mask.diff()
                clusters = (missing_diff == True).sum()

                if clusters <= 2:
                    return "clustered"
                else:
                    return "scattered"

        except Exception as e:
            logger.error(f"Missing pattern analysis failed: {str(e)}")
            return "unknown"

    async def _get_missing_data_recommendation(self, percentage: float) -> str:
        """
        Get recommendation based on missing data percentage
        """
        if percentage > 70:
            return "Consider removing this column as it has excessive missing data"
        elif percentage > 50:
            return "High missing data percentage - investigate data collection process"
        elif percentage > 25:
            return "Consider imputation methods or investigate missing data pattern"
        elif percentage > 10:
            return "Consider simple imputation methods (mean, median, mode)"
        else:
            return "Low missing data percentage - consider forward fill or drop missing rows"

    async def _calculate_completeness_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data completeness score
        """
        try:
            total_cells = df.size
            missing_cells = df.isnull().sum().sum()
            return ((total_cells - missing_cells) / total_cells) * 100
        except:
            return 0.0

    async def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data consistency score
        """
        try:
            consistency_score = 100.0

            # Check for type consistency
            for col in df.columns:
                if df[col].dtype == 'object':
                    inconsistencies = await self._check_type_consistency(df[col])
                    if inconsistencies:
                        consistency_score -= (len(inconsistencies) / len(df)) * 100

            return max(0, consistency_score)
        except:
            return 0.0

    async def _calculate_validity_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data validity score
        """
        try:
            validity_score = 100.0

            for col in df.columns:
                invalid_values = await self._check_validity(df[col])
                if invalid_values:
                    validity_score -= (len(invalid_values) / len(df)) * 100

            return max(0, validity_score)
        except:
            return 0.0

    async def _calculate_uniqueness_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data uniqueness score
        """
        try:
            duplicate_count = df.duplicated().sum()
            return ((len(df) - duplicate_count) / len(df)) * 100
        except:
            return 0.0

    async def _generate_column_metrics(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Generate detailed metrics for each column
        """
        metrics = {}

        try:
            for col in df.columns:
                # Calculate basic metrics with safe handling
                null_count = int(df[col].isnull().sum())
                null_percentage = (null_count / len(df)) * 100 if len(df) > 0 else 0
                unique_count = int(df[col].nunique())
                unique_percentage = (unique_count / len(df)) * 100 if len(df) > 0 else 0

                column_metrics = {
                    'data_type': str(df[col].dtype),
                    'non_null_count': int(df[col].count()),
                    'null_count': null_count,
                    'null_percentage': float(null_percentage),
                    'unique_count': unique_count,
                    'unique_percentage': float(unique_percentage)
                }

                # Add numeric-specific metrics
                if df[col].dtype in ['int64', 'float64']:
                    # Calculate metrics with NaN handling
                    mean_val = df[col].mean()
                    std_val = df[col].std()
                    min_val = df[col].min()
                    max_val = df[col].max()
                    median_val = df[col].median()

                    column_metrics.update({
                        'mean': None if pd.isna(mean_val) else float(mean_val),
                        'std': None if pd.isna(std_val) else float(std_val),
                        'min': None if pd.isna(min_val) else float(min_val),
                        'max': None if pd.isna(max_val) else float(max_val),
                        'median': None if pd.isna(median_val) else float(median_val),
                        'outlier_count': len(await self._detect_outliers(df[col]))
                    })

                # Add categorical-specific metrics
                if df[col].dtype == 'object':
                    value_counts = df[col].value_counts()
                    avg_length = df[col].astype(str).str.len().mean() if df[col].dtype == 'object' else None

                    column_metrics.update({
                        'most_frequent': value_counts.index[0] if len(value_counts) > 0 else None,
                        'most_frequent_count': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                        'avg_length': None if pd.isna(avg_length) else float(avg_length)
                    })

                metrics[col] = column_metrics

        except Exception as e:
            logger.error(f"Column metrics generation failed: {str(e)}")

        return metrics

    async def _generate_recommendations(self, issues: List[QualityIssue], df: pd.DataFrame) -> List[str]:
        """
        Generate actionable recommendations based on issues
        """
        recommendations = []

        try:
            # Critical issues
            critical_issues = [i for i in issues if i.severity == QualityIssueSeverity.CRITICAL]
            if critical_issues:
                recommendations.append(f"Address {len(critical_issues)} critical data quality issues immediately")

            # Missing data
            missing_issues = [i for i in issues if i.issue_type == QualityIssueType.MISSING_DATA]
            if missing_issues:
                high_missing = [i for i in missing_issues if i.percentage > 50]
                if high_missing:
                    recommendations.append(f"Consider removing {len(high_missing)} columns with >50% missing data")

            # Duplicates
            duplicate_issues = [i for i in issues if i.issue_type == QualityIssueType.DUPLICATE_RECORDS]
            if duplicate_issues:
                recommendations.append("Remove duplicate records to improve data quality")

            # Outliers
            outlier_issues = [i for i in issues if i.issue_type == QualityIssueType.OUTLIERS]
            if outlier_issues:
                recommendations.append(f"Review {len(outlier_issues)} columns with outliers")

            # General recommendations
            if len(issues) > 10:
                recommendations.append("Consider implementing data validation rules at the source")

            if not recommendations:
                recommendations.append("Data quality is good - no major issues detected")

        except Exception as e:
            logger.error(f"Recommendations generation failed: {str(e)}")

        return recommendations

    def get_quality_report(self) -> Optional[DataQualityReport]:
        """
        Get the generated quality report
        """
        return self.quality_report
