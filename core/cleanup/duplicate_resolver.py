"""
Duplicate detection and resolution for intelligent data cleanup.

This module provides comprehensive duplicate detection and resolution capabilities including:
- Exact and fuzzy duplicate detection
- Smart resolution strategies (keep first, keep last, merge, etc.)
- Confidence scoring for potential duplicates
- Multi-column and multi-criteria matching
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
from difflib import SequenceMatcher
import re
import logging
import uuid
from pydantic import BaseModel, Field

from .base import CleanupInterface, CleanupResult, CleanupIssue, CleanupSeverity, CleanupContext, CleanupStrategy

logger = logging.getLogger(__name__)


class DuplicateResolutionStrategy(str, Enum):
    """Strategies for resolving detected duplicates."""
    KEEP_FIRST = "keep_first"  # Keep the first occurrence
    KEEP_LAST = "keep_last"  # Keep the last occurrence
    KEEP_MOST_COMPLETE = "keep_most_complete"  # Keep record with most non-null values
    KEEP_MOST_RECENT = "keep_most_recent"  # Keep record with most recent timestamp
    MERGE_VALUES = "merge_values"  # Merge non-null values from duplicates
    FLAG_ONLY = "flag_only"  # Only flag duplicates, don't remove
    INTERACTIVE = "interactive"  # Require user decision


class DuplicateDetectionType(str, Enum):
    """Types of duplicate detection."""
    EXACT = "exact"  # Exact matches across all columns
    PARTIAL = "partial"  # Matches on subset of columns
    FUZZY = "fuzzy"  # Fuzzy string matching
    SEMANTIC = "semantic"  # Semantic similarity


class DuplicateGroup(BaseModel):
    """Represents a group of duplicate records."""

    group_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique group identifier")
    duplicate_indices: List[int] = Field(..., description="Row indices of duplicate records")
    detection_type: DuplicateDetectionType = Field(..., description="How duplicates were detected")
    matching_columns: List[str] = Field(..., description="Columns used for matching")
    similarity_score: float = Field(default=1.0, description="Similarity score (0-1)")
    confidence: float = Field(default=1.0, description="Confidence in duplicate detection")
    suggested_resolution: DuplicateResolutionStrategy = Field(..., description="Suggested resolution strategy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DuplicateResult(CleanupResult):
    """Specialized result for duplicate resolution operations."""

    detection_type: DuplicateDetectionType = Field(..., description="Type of detection used")
    resolution_strategy: DuplicateResolutionStrategy = Field(..., description="Strategy used for resolution")
    duplicate_groups: List[DuplicateGroup] = Field(default_factory=list, description="Groups of duplicates found")
    duplicates_detected: int = Field(default=0, description="Number of duplicate records detected")
    duplicates_resolved: int = Field(default=0, description="Number of duplicate records resolved")
    records_merged: int = Field(default=0, description="Number of records created by merging")


class DuplicateResolver(CleanupInterface):
    """Comprehensive duplicate detection and resolution system."""

    def __init__(self):
        self.supported_strategies = list(DuplicateResolutionStrategy)
        self.supported_detection_types = list(DuplicateDetectionType)
        self.default_fuzzy_threshold = 0.8

    async def clean(self, data: pd.DataFrame, context: Optional[CleanupContext] = None, **kwargs) -> DuplicateResult:
        """
        Detect and resolve duplicates in the provided DataFrame.

        Args:
            data: DataFrame to clean
            context: Cleanup context with preferences
            **kwargs: Additional parameters (detection_type, strategy, columns, thresholds)

        Returns:
            DuplicateResult with cleaned data and operation details
        """
        start_time = datetime.utcnow()

        # Validate input
        try:
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Input must be a pandas DataFrame")

            if len(data) == 0:
                logger.warning("Input DataFrame is empty")
                return DuplicateResult(
                    is_successful=True,
                    cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                    detection_type=DuplicateDetectionType.EXACT,
                    resolution_strategy=DuplicateResolutionStrategy.FLAG_ONLY,
                    cleaned_data=data.copy(),
                    rollback_info={}
                )

            try:
                if not self.validate_input(data):
                    logger.warning("Input validation failed for duplicate resolver")
                    return DuplicateResult(
                        is_successful=False,
                        cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                        detection_type=DuplicateDetectionType.EXACT,
                        resolution_strategy=DuplicateResolutionStrategy.FLAG_ONLY,
                        cleaned_data=data.copy(),
                        rollback_info={}
                    )
            except Exception as e:
                logger.error(f"Input validation error in duplicate resolver: {str(e)}")
                return DuplicateResult(
                    is_successful=False,
                    cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                    detection_type=DuplicateDetectionType.EXACT,
                    resolution_strategy=DuplicateResolutionStrategy.FLAG_ONLY,
                    cleaned_data=data.copy(),
                    rollback_info={}
                )

        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return DuplicateResult(
                is_successful=False,
                cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
                detection_type=DuplicateDetectionType.EXACT,
                resolution_strategy=DuplicateResolutionStrategy.FLAG_ONLY,
                cleaned_data=data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(),
                rollback_info={}
            )

        # Extract parameters
        detection_type = kwargs.get('detection_type', DuplicateDetectionType.EXACT)
        strategy = kwargs.get('strategy', DuplicateResolutionStrategy.FLAG_ONLY)
        columns = kwargs.get('columns', None)  # Specific columns for duplicate detection
        fuzzy_threshold = kwargs.get('fuzzy_threshold', self.default_fuzzy_threshold)

        # Use context strategy if provided
        if context and context.cleanup_strategy:
            if context.cleanup_strategy == CleanupStrategy.CONSERVATIVE:
                strategy = DuplicateResolutionStrategy.FLAG_ONLY
            elif context.cleanup_strategy == CleanupStrategy.AUTOMATIC:
                strategy = kwargs.get('strategy', DuplicateResolutionStrategy.KEEP_FIRST)

        result = DuplicateResult(
            is_successful=True,
            cleanup_strategy_used=context.cleanup_strategy if context else CleanupStrategy.SUGGEST,
            detection_type=detection_type,
            resolution_strategy=strategy,
            cleaned_data=data.copy(),
            rollback_info={}
        )

        try:
            # Detect duplicates
            duplicate_groups = await self._detect_duplicates(data, detection_type, columns, fuzzy_threshold)
            result.duplicate_groups = duplicate_groups
            result.duplicates_detected = sum(len(group.duplicate_indices) for group in duplicate_groups)

            # Create cleanup issues
            issues = await self._create_duplicate_issues(data, duplicate_groups)
            result.issues_found = issues

            # Resolve duplicates based on strategy
            if strategy != DuplicateResolutionStrategy.FLAG_ONLY:
                resolved_data, resolved_count, merged_count = await self._resolve_duplicates(
                    data, duplicate_groups, strategy, context
                )
                result.cleaned_data = resolved_data
                result.duplicates_resolved = resolved_count
                result.records_merged = merged_count
                result.rows_affected = resolved_count

                # Mark issues as resolved
                resolved_issues = 0
                for issue in issues:
                    if resolved_issues < resolved_count:
                        result.mark_issue_resolved(issue.id)
                        resolved_issues += 1

            # Calculate execution time
            end_time = datetime.utcnow()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Generate additional recommendations
            result.additional_recommendations = await self._generate_recommendations(
                data, duplicate_groups, detection_type, strategy
            )

        except Exception as e:
            logger.error(f"Duplicate resolution failed: {str(e)}")
            result.is_successful = False
            result.add_issue(CleanupIssue(
                issue_type="duplicate_processing_error",
                severity=CleanupSeverity.CRITICAL,
                message=f"Duplicate processing failed: {str(e)}",
                field="",
                suggested_action="Review data format and try different detection method",
                confidence=1.0,
                estimated_impact="Processing cannot continue"
            ))

        return result

    async def analyze_data(self, data: pd.DataFrame, context: Optional[CleanupContext] = None) -> List[CleanupIssue]:
        """Analyze data to identify duplicates without resolving them."""
        # Try multiple detection types for comprehensive analysis
        detection_types = [DuplicateDetectionType.EXACT, DuplicateDetectionType.PARTIAL, DuplicateDetectionType.FUZZY]
        all_issues = []

        for detection_type in detection_types:
            try:
                duplicate_groups = await self._detect_duplicates(data, detection_type, None, self.default_fuzzy_threshold)
                issues = await self._create_duplicate_issues(data, duplicate_groups)
                all_issues.extend(issues)
            except Exception as e:
                logger.warning(f"Duplicate analysis with {detection_type} failed: {str(e)}")

        # Remove duplicates based on same group IDs
        unique_issues = self._deduplicate_issues(all_issues)
        return unique_issues

    async def _detect_duplicates(self, data: pd.DataFrame, detection_type: DuplicateDetectionType,
                               columns: Optional[List[str]], fuzzy_threshold: float) -> List[DuplicateGroup]:
        """Detect duplicates using the specified detection type."""
        duplicate_groups = []

        if detection_type == DuplicateDetectionType.EXACT:
            duplicate_groups = await self._detect_exact_duplicates(data, columns)

        elif detection_type == DuplicateDetectionType.PARTIAL:
            duplicate_groups = await self._detect_partial_duplicates(data, columns)

        elif detection_type == DuplicateDetectionType.FUZZY:
            duplicate_groups = await self._detect_fuzzy_duplicates(data, columns, fuzzy_threshold)

        elif detection_type == DuplicateDetectionType.SEMANTIC:
            # Placeholder for semantic duplicate detection
            # This would require more advanced NLP techniques
            duplicate_groups = await self._detect_exact_duplicates(data, columns)

        return duplicate_groups

    async def _detect_exact_duplicates(self, data: pd.DataFrame, columns: Optional[List[str]]) -> List[DuplicateGroup]:
        """Detect exact duplicates."""
        if columns is None:
            # Use all columns for exact matching
            subset_cols = None
        else:
            subset_cols = columns

        # Find duplicate rows
        duplicate_mask = data.duplicated(subset=subset_cols, keep=False)
        duplicate_data = data[duplicate_mask]

        if len(duplicate_data) == 0:
            return []

        # Group duplicates by their values
        groups = []
        processed_indices = set()

        for idx, row in duplicate_data.iterrows():
            if idx in processed_indices:
                continue

            # Find all rows that match this one
            if subset_cols:
                # Compare each column individually to avoid DataFrame boolean evaluation
                matching_mask = pd.Series([True] * len(data), index=data.index)
                for col in subset_cols:
                    # Ensure we're comparing scalar values
                    row_value = row[col]
                    if hasattr(row_value, 'iloc'):
                        row_value = row_value.iloc[0] if len(row_value) > 0 else None
                    matching_mask &= (data[col] == row_value)
            else:
                # Compare each column individually to avoid DataFrame boolean evaluation
                matching_mask = pd.Series([True] * len(data), index=data.index)
                for col in data.columns:
                    # Ensure we're comparing scalar values
                    row_value = row[col]
                    if hasattr(row_value, 'iloc'):
                        row_value = row_value.iloc[0] if len(row_value) > 0 else None
                    matching_mask &= (data[col] == row_value)

            matching_indices = data[matching_mask].index.tolist()

            if len(matching_indices) > 1:
                groups.append(DuplicateGroup(
                    duplicate_indices=matching_indices,
                    detection_type=DuplicateDetectionType.EXACT,
                    matching_columns=subset_cols or data.columns.tolist(),
                    similarity_score=1.0,
                    confidence=1.0,
                    suggested_resolution=DuplicateResolutionStrategy.KEEP_FIRST
                ))

                processed_indices.update(matching_indices)

        return groups

    async def _detect_partial_duplicates(self, data: pd.DataFrame, columns: Optional[List[str]]) -> List[DuplicateGroup]:
        """Detect partial duplicates based on key columns."""
        if columns is None:
            # Use heuristics to identify key columns
            key_columns = self._identify_key_columns(data)
        else:
            key_columns = columns

        if not key_columns:
            return []

        # Find duplicates based on key columns
        duplicate_mask = data.duplicated(subset=key_columns, keep=False)
        duplicate_data = data[duplicate_mask]

        if len(duplicate_data) == 0:
            return []

        # Group duplicates by key column values
        groups = []
        processed_indices = set()

        for idx, row in duplicate_data.iterrows():
            if idx in processed_indices:
                continue

            # Find all rows that match on key columns
            # Compare each column individually to avoid DataFrame boolean evaluation
            matching_mask = pd.Series([True] * len(data), index=data.index)
            for col in key_columns:
                # Ensure we're comparing scalar values
                row_value = row[col]
                if hasattr(row_value, 'iloc'):
                    row_value = row_value.iloc[0] if len(row_value) > 0 else None
                matching_mask &= (data[col] == row_value)
            matching_indices = data[matching_mask].index.tolist()

            if len(matching_indices) > 1:
                # Calculate similarity score based on how many non-key columns match
                similarity = self._calculate_partial_similarity(data.loc[matching_indices], key_columns)

                groups.append(DuplicateGroup(
                    duplicate_indices=matching_indices,
                    detection_type=DuplicateDetectionType.PARTIAL,
                    matching_columns=key_columns,
                    similarity_score=similarity,
                    confidence=0.8,  # Lower confidence for partial matches
                    suggested_resolution=DuplicateResolutionStrategy.KEEP_MOST_COMPLETE
                ))

                processed_indices.update(matching_indices)

        return groups

    async def _detect_fuzzy_duplicates(self, data: pd.DataFrame, columns: Optional[List[str]],
                                     threshold: float) -> List[DuplicateGroup]:
        """Detect fuzzy duplicates using string similarity."""
        if columns is None:
            # Use string columns for fuzzy matching
            string_columns = data.select_dtypes(include=['object']).columns.tolist()
        else:
            string_columns = [col for col in columns if col in data.columns]

        if not string_columns:
            return []

        groups = []
        processed_indices = set()

        # Compare each row with every other row
        for i in range(len(data)):
            if i in processed_indices:
                continue

            similar_indices = [i]
            row_i = data.iloc[i]

            for j in range(i + 1, len(data)):
                if j in processed_indices:
                    continue

                row_j = data.iloc[j]
                similarity = self._calculate_fuzzy_similarity(row_i, row_j, string_columns)

                if similarity >= threshold:
                    similar_indices.append(j)

            if len(similar_indices) > 1:
                avg_similarity = self._calculate_group_similarity(data.iloc[similar_indices], string_columns)

                groups.append(DuplicateGroup(
                    duplicate_indices=similar_indices,
                    detection_type=DuplicateDetectionType.FUZZY,
                    matching_columns=string_columns,
                    similarity_score=avg_similarity,
                    confidence=avg_similarity,  # Confidence equals similarity for fuzzy matching
                    suggested_resolution=DuplicateResolutionStrategy.KEEP_MOST_COMPLETE
                ))

                processed_indices.update(similar_indices)

        return groups

    def _identify_key_columns(self, data: pd.DataFrame) -> List[str]:
        """Identify columns that are likely to be key identifiers."""
        key_columns = []

        for column in data.columns:
            # Look for columns that might be identifiers
            col_name_lower = column.lower()

            # Check for ID-like column names
            if any(identifier in col_name_lower for identifier in ['id', 'key', 'identifier', 'code']):
                key_columns.append(column)
                continue

            # Check for name-like columns
            if any(name_indicator in col_name_lower for name_indicator in ['name', 'title', 'label']):
                key_columns.append(column)
                continue

            # Check for columns with high uniqueness
            uniqueness_ratio = data[column].nunique() / len(data)
            if uniqueness_ratio > 0.7:  # More than 70% unique values
                key_columns.append(column)

        # Limit to most promising columns
        return key_columns[:3]  # Maximum 3 key columns

    def _calculate_partial_similarity(self, duplicate_rows: pd.DataFrame, key_columns: List[str]) -> float:
        """Calculate similarity score for partial duplicates."""
        non_key_columns = [col for col in duplicate_rows.columns if col not in key_columns]

        if not non_key_columns:
            return 1.0

        total_matches = 0
        total_comparisons = 0

        # Compare all pairs of rows
        for i in range(len(duplicate_rows)):
            for j in range(i + 1, len(duplicate_rows)):
                row_i = duplicate_rows.iloc[i]
                row_j = duplicate_rows.iloc[j]

                for col in non_key_columns:
                    val_i = row_i[col]
                    val_j = row_j[col]

                    # Skip if either value is null
                    if pd.isna(val_i) or pd.isna(val_j):
                        continue

                    total_comparisons += 1
                    if val_i == val_j:
                        total_matches += 1

        return total_matches / total_comparisons if total_comparisons > 0 else 1.0

    def _calculate_fuzzy_similarity(self, row1: pd.Series, row2: pd.Series, columns: List[str]) -> float:
        """Calculate fuzzy similarity between two rows."""
        try:
            similarities = []

            for column in columns:
                if column not in row1.index or column not in row2.index:
                    continue

                val1 = str(row1[column]) if pd.notna(row1[column]) else ""
                val2 = str(row2[column]) if pd.notna(row2[column]) else ""

                if val1 == "" and val2 == "":
                    continue  # Skip empty values

                # Use SequenceMatcher for string similarity
                similarity = SequenceMatcher(None, val1.lower(), val2.lower()).ratio()
                similarities.append(similarity)

            return float(np.mean(similarities)) if similarities else 0.0

        except Exception as e:
            logger.warning(f"Error calculating fuzzy similarity: {str(e)}")
            return 0.0

    def _calculate_group_similarity(self, group_rows: pd.DataFrame, columns: List[str]) -> float:
        """Calculate average similarity within a group of rows."""
        try:
            if len(group_rows) <= 1:
                return 1.0

            similarities = []
            for i in range(len(group_rows)):
                for j in range(i + 1, len(group_rows)):
                    similarity = self._calculate_fuzzy_similarity(
                        group_rows.iloc[i], group_rows.iloc[j], columns
                    )
                    similarities.append(similarity)

            return float(np.mean(similarities)) if similarities else 1.0

        except Exception as e:
            logger.warning(f"Error calculating group similarity: {str(e)}")
            return 1.0

    async def _create_duplicate_issues(self, data: pd.DataFrame, duplicate_groups: List[DuplicateGroup]) -> List[CleanupIssue]:
        """Create CleanupIssue objects for detected duplicates."""
        issues = []

        for group in duplicate_groups:
            # Determine severity based on group size and confidence
            severity = self._determine_duplicate_severity(len(group.duplicate_indices), group.confidence)

            issue = CleanupIssue(
                issue_type="duplicate",
                severity=severity,
                message=f"Detected {len(group.duplicate_indices)} duplicate records (similarity: {group.similarity_score:.2f})",
                field=", ".join(group.matching_columns),
                row_indices=group.duplicate_indices,
                affected_values=[],  # Don't store all values to keep size manageable
                suggested_action=f"Resolve duplicates using {group.suggested_resolution.value} strategy",
                confidence=group.confidence,
                estimated_impact=f"Affects {len(group.duplicate_indices)} rows",
                metadata={
                    "group_id": group.group_id,
                    "detection_type": group.detection_type.value,
                    "similarity_score": group.similarity_score,
                    "matching_columns": group.matching_columns
                }
            )
            issues.append(issue)

        return issues

    def _determine_duplicate_severity(self, group_size: int, confidence: float) -> CleanupSeverity:
        """Determine severity of duplicates based on group size and confidence."""
        if confidence > 0.9 and group_size > 5:
            return CleanupSeverity.HIGH
        elif confidence > 0.8 and group_size > 3:
            return CleanupSeverity.MEDIUM
        elif confidence > 0.6:
            return CleanupSeverity.LOW
        else:
            return CleanupSeverity.INFO

    async def _resolve_duplicates(self, data: pd.DataFrame, duplicate_groups: List[DuplicateGroup],
                                strategy: DuplicateResolutionStrategy, context: Optional[CleanupContext]) -> Tuple[pd.DataFrame, int, int]:
        """Resolve duplicates based on the specified strategy."""
        cleaned_data = data.copy()
        total_resolved = 0
        total_merged = 0

        for group in duplicate_groups:
            if len(group.duplicate_indices) <= 1:
                continue

            if strategy == DuplicateResolutionStrategy.KEEP_FIRST:
                # Keep first occurrence, remove others
                indices_to_remove = group.duplicate_indices[1:]
                cleaned_data = cleaned_data.drop(indices_to_remove)
                total_resolved += len(indices_to_remove)

            elif strategy == DuplicateResolutionStrategy.KEEP_LAST:
                # Keep last occurrence, remove others
                indices_to_remove = group.duplicate_indices[:-1]
                cleaned_data = cleaned_data.drop(indices_to_remove)
                total_resolved += len(indices_to_remove)

            elif strategy == DuplicateResolutionStrategy.KEEP_MOST_COMPLETE:
                # Keep record with most non-null values
                duplicate_rows = data.loc[group.duplicate_indices]
                completeness_scores = duplicate_rows.notna().sum(axis=1)
                best_index = completeness_scores.idxmax()

                indices_to_remove = [idx for idx in group.duplicate_indices if idx != best_index]
                cleaned_data = cleaned_data.drop(indices_to_remove)
                total_resolved += len(indices_to_remove)

            elif strategy == DuplicateResolutionStrategy.MERGE_VALUES:
                # Merge non-null values from all duplicates
                merged_row = await self._merge_duplicate_rows(data.loc[group.duplicate_indices])

                # Remove original duplicates and add merged row
                cleaned_data = cleaned_data.drop(group.duplicate_indices)
                cleaned_data = pd.concat([cleaned_data, merged_row.to_frame().T], ignore_index=True)

                total_resolved += len(group.duplicate_indices)
                total_merged += 1

        return cleaned_data, total_resolved, total_merged

    async def _merge_duplicate_rows(self, duplicate_rows: pd.DataFrame) -> pd.Series:
        """Merge multiple duplicate rows into a single row."""
        merged_row = duplicate_rows.iloc[0].copy()

        for column in duplicate_rows.columns:
            column_values = duplicate_rows[column].dropna()

            if len(column_values) == 0:
                continue
            elif len(column_values) == 1:
                merged_row[column] = column_values.iloc[0]
            else:
                # Use most frequent value, or first if tie
                value_counts = column_values.value_counts()
                merged_row[column] = value_counts.index[0]

        return merged_row

    async def _generate_recommendations(self, data: pd.DataFrame, duplicate_groups: List[DuplicateGroup],
                                      detection_type: DuplicateDetectionType, strategy: DuplicateResolutionStrategy) -> List[str]:
        """Generate additional recommendations based on duplicate analysis."""
        recommendations = []

        total_duplicates = sum(len(group.duplicate_indices) for group in duplicate_groups)
        duplicate_percentage = (total_duplicates / len(data)) * 100 if len(data) > 0 else 0

        if duplicate_percentage > 20:
            recommendations.append("High percentage of duplicates detected. Review data collection and integration processes.")

        if duplicate_percentage > 10:
            recommendations.append("Consider implementing data deduplication as part of your regular data pipeline.")

        if strategy == DuplicateResolutionStrategy.FLAG_ONLY:
            recommendations.append("Duplicates have been flagged. Consider applying automated resolution if appropriate.")

        # Detection-specific recommendations
        if detection_type == DuplicateDetectionType.FUZZY:
            high_confidence_groups = [g for g in duplicate_groups if g.confidence > 0.9]
            if len(high_confidence_groups) > 0:
                recommendations.append(f"Found {len(high_confidence_groups)} high-confidence fuzzy duplicate groups that can be safely resolved.")

        return recommendations

    def _deduplicate_issues(self, issues: List[CleanupIssue]) -> List[CleanupIssue]:
        """Remove duplicate issues that refer to the same duplicate groups."""
        seen_group_ids = set()
        unique_issues = []

        for issue in issues:
            group_id = issue.metadata.get('group_id')
            if group_id and group_id not in seen_group_ids:
                seen_group_ids.add(group_id)
                unique_issues.append(issue)
            elif not group_id:
                unique_issues.append(issue)

        return unique_issues

    def get_cleanup_info(self) -> Dict[str, Any]:
        """Get information about the duplicate resolver."""
        return {
            "name": "DuplicateResolver",
            "version": "1.0.0",
            "description": "Comprehensive duplicate detection and resolution system",
            "supported_detection_types": [dt.value for dt in self.supported_detection_types],
            "supported_resolution_strategies": [strategy.value for strategy in self.supported_strategies],
            "default_fuzzy_threshold": self.default_fuzzy_threshold,
            "capabilities": [
                "Exact duplicate detection",
                "Partial duplicate detection",
                "Fuzzy string matching",
                "Smart resolution strategies",
                "Confidence scoring",
                "Batch processing"
            ]
        }
