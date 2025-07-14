"""
Automatic metadata extraction system.

This module provides comprehensive automatic metadata extraction including:
- Column purpose identification (ID, name, date, amount, etc.)
- Business context inference
- Relationship mapping between columns
- Data lineage tracking
"""

import re
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid

from .base import MetadataInterface, MetadataType, MetadataStatus, MetadataLineage, MetadataContext


class ColumnPurpose(str, Enum):
    """Identified purposes for columns."""
    ID = "id"
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    NAME = "name"
    DESCRIPTION = "description"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    AMOUNT = "amount"
    PRICE = "price"
    QUANTITY = "quantity"
    PERCENTAGE = "percentage"
    RATING = "rating"
    STATUS = "status"
    CATEGORY = "category"
    TAG = "tag"
    URL = "url"
    COORDINATE = "coordinate"
    BINARY_FLAG = "binary_flag"
    MEASUREMENT = "measurement"
    CODE = "code"
    UNKNOWN = "unknown"


class RelationshipType(str, Enum):
    """Types of relationships between columns."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"
    HIERARCHICAL = "hierarchical"
    FUNCTIONAL_DEPENDENCY = "functional_dependency"
    CORRELATION = "correlation"


class ColumnMetadata(BaseModel):
    """Comprehensive metadata for a single column."""

    column_name: str = Field(..., description="Original column name")
    display_name: Optional[str] = Field(None, description="Human-friendly display name")
    purpose: ColumnPurpose = Field(default=ColumnPurpose.UNKNOWN)
    data_type: str = Field(..., description="Detected data type")
    business_meaning: Optional[str] = Field(None, description="Business interpretation")
    description: Optional[str] = Field(None, description="Auto-generated description")

    # Statistical metadata
    null_count: int = Field(default=0)
    unique_count: int = Field(default=0)
    completeness: float = Field(default=0.0, description="Percentage of non-null values")
    uniqueness: float = Field(default=0.0, description="Percentage of unique values")

    # Pattern metadata
    patterns: List[str] = Field(default_factory=list, description="Detected patterns")
    format_hints: List[str] = Field(default_factory=list, description="Format suggestions")

    # Quality metadata
    quality_score: float = Field(default=0.0, description="Overall quality score")
    quality_issues: List[str] = Field(default_factory=list)

    # Relationship metadata
    potential_keys: List[str] = Field(default_factory=list, description="Potential key relationships")
    correlations: Dict[str, float] = Field(default_factory=dict, description="Correlations with other columns")

    # Business metadata
    business_domain: Optional[str] = Field(None, description="Business domain classification")
    sensitivity_level: Optional[str] = Field(None, description="Data sensitivity classification")

    # Extraction metadata
    confidence_score: float = Field(default=0.0, description="Confidence in purpose identification")
    extraction_method: str = Field(default="automatic", description="How metadata was extracted")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DatasetMetadata(BaseModel):
    """Comprehensive metadata for an entire dataset."""

    dataset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")

    # Column metadata
    columns: Dict[str, ColumnMetadata] = Field(default_factory=dict)

    # Dataset-level statistics
    total_rows: int = Field(default=0)
    total_columns: int = Field(default=0)
    completeness: float = Field(default=0.0)
    quality_score: float = Field(default=0.0)

    # Relationships
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: Dict[str, str] = Field(default_factory=dict)

    # Business context
    business_domain: Optional[str] = Field(None)
    use_cases: List[str] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)

    # Lineage
    source_systems: List[str] = Field(default_factory=list)
    lineage: List[MetadataLineage] = Field(default_factory=list)

    # Extraction metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_version: str = Field(default="1.0")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetadataExtractionResult(BaseModel):
    """Result of metadata extraction operation."""

    success: bool = Field(default=True)
    dataset_metadata: Optional[DatasetMetadata] = Field(None)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


class ColumnPurposeDetector:
    """Detects the purpose of columns based on name patterns and data characteristics."""

    def __init__(self):
        # Define patterns for different column purposes
        self.purpose_patterns = {
            ColumnPurpose.ID: [
                r'.*id$', r'^id.*', r'.*_id$', r'^.*_id.*$',
                r'.*identifier.*', r'.*key$', r'^key.*'
            ],
            ColumnPurpose.PRIMARY_KEY: [
                r'^id$', r'^primary_key$', r'^pk$', r'.*_pk$'
            ],
            ColumnPurpose.FOREIGN_KEY: [
                r'.*_id$', r'.*_fk$', r'.*_key$', r'foreign.*key'
            ],
            ColumnPurpose.NAME: [
                r'.*name.*', r'.*title.*', r'.*label.*', r'.*full_name.*',
                r'first.*name', r'last.*name', r'.*surname.*'
            ],
            ColumnPurpose.EMAIL: [
                r'.*email.*', r'.*e_mail.*', r'.*mail.*'
            ],
            ColumnPurpose.PHONE: [
                r'.*phone.*', r'.*telephone.*', r'.*mobile.*', r'.*cell.*'
            ],
            ColumnPurpose.ADDRESS: [
                r'.*address.*', r'.*location.*', r'.*street.*', r'.*city.*',
                r'.*state.*', r'.*country.*', r'.*zip.*', r'.*postal.*'
            ],
            ColumnPurpose.DATE: [
                r'.*date.*', r'.*day.*', r'.*month.*', r'.*year.*'
            ],
            ColumnPurpose.DATETIME: [
                r'.*datetime.*', r'.*timestamp.*', r'.*time.*'
            ],
            ColumnPurpose.AMOUNT: [
                r'.*amount.*', r'.*total.*', r'.*sum.*', r'.*balance.*'
            ],
            ColumnPurpose.PRICE: [
                r'.*price.*', r'.*cost.*', r'.*rate.*', r'.*fee.*'
            ],
            ColumnPurpose.QUANTITY: [
                r'.*quantity.*', r'.*count.*', r'.*number.*', r'.*qty.*'
            ],
            ColumnPurpose.PERCENTAGE: [
                r'.*percent.*', r'.*pct.*', r'.*ratio.*', r'.*rate.*'
            ],
            ColumnPurpose.STATUS: [
                r'.*status.*', r'.*state.*', r'.*condition.*'
            ],
            ColumnPurpose.CATEGORY: [
                r'.*category.*', r'.*type.*', r'.*class.*', r'.*group.*'
            ]
        }

    def detect_purpose(self, column_name: str, series: pd.Series) -> Tuple[ColumnPurpose, float]:
        """
        Detect the purpose of a column based on name and data characteristics.

        Returns:
            Tuple of (detected_purpose, confidence_score)
        """
        column_lower = column_name.lower()

        # Check name patterns
        name_scores = {}
        for purpose, patterns in self.purpose_patterns.items():
            for pattern in patterns:
                if re.match(pattern, column_lower):
                    name_scores[purpose] = name_scores.get(purpose, 0) + 1

        # Check data characteristics
        data_scores = self._analyze_data_characteristics(series)

        # Combine name and data scores
        combined_scores = {}
        for purpose in ColumnPurpose:
            name_score = name_scores.get(purpose, 0) * 0.6  # Weight name patterns higher
            data_score = data_scores.get(purpose, 0) * 0.4
            combined_scores[purpose] = name_score + data_score

        # Find best match
        if not combined_scores or max(combined_scores.values()) == 0:
            return ColumnPurpose.UNKNOWN, 0.0

        best_purpose = max(combined_scores, key=lambda x: combined_scores[x])
        confidence = min(combined_scores[best_purpose] / 10.0, 1.0)  # Normalize to 0-1

        return best_purpose, confidence

    def _analyze_data_characteristics(self, series: pd.Series) -> Dict[ColumnPurpose, float]:
        """Analyze data characteristics to infer column purpose."""
        scores = {}

        if len(series) == 0:
            return scores

        # Sample non-null values
        non_null_values = series.dropna()
        if len(non_null_values) == 0:
            return scores

        sample_values = non_null_values.head(100).astype(str)

        # ID patterns
        if self._looks_like_id(sample_values):
            scores[ColumnPurpose.ID] = 3.0

        # Email patterns
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if sample_values.str.match(email_pattern).any():
            scores[ColumnPurpose.EMAIL] = 5.0

        # Phone patterns
        phone_pattern = r'^[\+]?[\d\s\-\(\)]{10,}$'
        if sample_values.str.match(phone_pattern).any():
            scores[ColumnPurpose.PHONE] = 4.0

        # Date/datetime patterns
        if self._looks_like_date(sample_values):
            scores[ColumnPurpose.DATE] = 4.0

        # Numeric patterns
        if pd.api.types.is_numeric_dtype(series):
            if self._looks_like_percentage(series):
                scores[ColumnPurpose.PERCENTAGE] = 3.0
            elif self._looks_like_amount(series):
                scores[ColumnPurpose.AMOUNT] = 2.0

        # Binary flag patterns
        if self._looks_like_binary_flag(series):
            scores[ColumnPurpose.BINARY_FLAG] = 4.0

        return scores

    def _looks_like_id(self, sample_values: pd.Series) -> bool:
        """Check if values look like IDs."""
        # Check for UUID patterns
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if sample_values.str.match(uuid_pattern, case=False).any():
            return True

        # Check for incremental IDs
        try:
            numeric_values = pd.to_numeric(sample_values, errors='coerce')
            if not numeric_values.isna().all():
                # Check if values are mostly incremental
                sorted_values = numeric_values.dropna().sort_values()
                if len(sorted_values) > 1:
                    diffs = sorted_values.diff().dropna()
                    if (diffs == 1).sum() / len(diffs) > 0.8:
                        return True
        except:
            pass

        return False

    def _looks_like_date(self, sample_values: pd.Series) -> bool:
        """Check if values look like dates."""
        try:
            pd.to_datetime(sample_values.head(10), errors='raise')
            return True
        except:
            return False

    def _looks_like_percentage(self, series: pd.Series) -> bool:
        """Check if numeric values look like percentages."""
        if not pd.api.types.is_numeric_dtype(series):
            return False

        non_null = series.dropna()
        if len(non_null) == 0:
            return False

        # Check if values are mostly between 0-100 or 0-1
        between_0_100 = ((non_null >= 0) & (non_null <= 100)).sum() / len(non_null)
        between_0_1 = ((non_null >= 0) & (non_null <= 1)).sum() / len(non_null)

        return between_0_100 > 0.8 or between_0_1 > 0.8

    def _looks_like_amount(self, series: pd.Series) -> bool:
        """Check if numeric values look like monetary amounts."""
        if not pd.api.types.is_numeric_dtype(series):
            return False

        non_null = series.dropna()
        if len(non_null) == 0:
            return False

        # Check for typical amount characteristics
        # - Positive values
        # - Reasonable decimal places (0-2)
        positive_ratio = (non_null > 0).sum() / len(non_null)

        return positive_ratio > 0.7

    def _looks_like_binary_flag(self, series: pd.Series) -> bool:
        """Check if values look like binary flags."""
        unique_values = set(series.dropna().astype(str).str.lower())

        binary_patterns = [
            {'true', 'false'},
            {'yes', 'no'},
            {'y', 'n'},
            {'1', '0'},
            {'active', 'inactive'},
            {'enabled', 'disabled'}
        ]

        return any(unique_values.issubset(pattern) for pattern in binary_patterns)


class BusinessContextInferencer:
    """Infers business context and meaning from data patterns."""

    def __init__(self):
        self.domain_keywords = {
            'finance': ['amount', 'price', 'cost', 'revenue', 'profit', 'balance', 'payment'],
            'hr': ['employee', 'salary', 'department', 'manager', 'hire_date', 'position'],
            'sales': ['customer', 'order', 'product', 'quantity', 'discount', 'commission'],
            'marketing': ['campaign', 'lead', 'conversion', 'click', 'impression', 'roi'],
            'healthcare': ['patient', 'diagnosis', 'treatment', 'medication', 'symptom'],
            'education': ['student', 'course', 'grade', 'semester', 'teacher', 'enrollment']
        }

    def infer_business_domain(self, column_names: List[str]) -> Tuple[Optional[str], float]:
        """
        Infer business domain from column names.

        Returns:
            Tuple of (domain, confidence_score)
        """
        domain_scores = {}

        for domain, keywords in self.domain_keywords.items():
            score = 0
            for col_name in column_names:
                col_lower = col_name.lower()
                for keyword in keywords:
                    if keyword in col_lower:
                        score += 1

            if score > 0:
                domain_scores[domain] = score / len(column_names)

        if not domain_scores:
            return None, 0.0

        best_domain = max(domain_scores, key=lambda x: domain_scores[x])
        confidence = min(domain_scores[best_domain], 1.0)

        return best_domain, confidence

    def generate_business_meaning(self, column_metadata: ColumnMetadata) -> Optional[str]:
        """Generate business meaning description for a column."""
        purpose = column_metadata.purpose
        column_name = column_metadata.column_name

        purpose_meanings = {
            ColumnPurpose.ID: f"Unique identifier for records in the {column_name} dimension",
            ColumnPurpose.PRIMARY_KEY: f"Primary key that uniquely identifies each record",
            ColumnPurpose.FOREIGN_KEY: f"Reference key linking to related data in another table",
            ColumnPurpose.NAME: f"Name or title field for identification purposes",
            ColumnPurpose.EMAIL: f"Email address for communication and identification",
            ColumnPurpose.PHONE: f"Phone number for contact purposes",
            ColumnPurpose.ADDRESS: f"Physical or mailing address information",
            ColumnPurpose.DATE: f"Date information for temporal analysis",
            ColumnPurpose.DATETIME: f"Timestamp for tracking when events occurred",
            ColumnPurpose.AMOUNT: f"Monetary or quantity amount for financial analysis",
            ColumnPurpose.PRICE: f"Price or cost information for financial calculations",
            ColumnPurpose.QUANTITY: f"Count or quantity measure for inventory or volume analysis",
            ColumnPurpose.PERCENTAGE: f"Percentage or ratio for performance measurement",
            ColumnPurpose.STATUS: f"Status or state information for workflow tracking",
            ColumnPurpose.CATEGORY: f"Categorical classification for grouping and segmentation"
        }

        return purpose_meanings.get(purpose)


class RelationshipMapper:
    """Maps and identifies relationships between columns."""

    def detect_relationships(self, df: pd.DataFrame, metadata: Dict[str, ColumnMetadata]) -> List[Dict[str, Any]]:
        """Detect relationships between columns in the dataset."""
        relationships = []

        # Detect potential foreign key relationships
        relationships.extend(self._detect_foreign_keys(df, metadata))

        # Detect hierarchical relationships
        relationships.extend(self._detect_hierarchical_relationships(df, metadata))

        # Detect functional dependencies
        relationships.extend(self._detect_functional_dependencies(df, metadata))

        return relationships

    def _detect_foreign_keys(self, df: pd.DataFrame, metadata: Dict[str, ColumnMetadata]) -> List[Dict[str, Any]]:
        """Detect potential foreign key relationships."""
        relationships = []

        id_columns = [col for col, meta in metadata.items() if meta.purpose == ColumnPurpose.ID]
        fk_columns = [col for col, meta in metadata.items() if meta.purpose == ColumnPurpose.FOREIGN_KEY]

        for fk_col in fk_columns:
            for id_col in id_columns:
                if fk_col != id_col:
                    # Check if FK values exist in ID column
                    fk_values = set(df[fk_col].dropna())
                    id_values = set(df[id_col].dropna())

                    overlap_ratio = len(fk_values.intersection(id_values)) / len(fk_values) if fk_values else 0

                    if overlap_ratio > 0.7:  # 70% overlap threshold
                        relationships.append({
                            'type': RelationshipType.MANY_TO_ONE,
                            'from_column': fk_col,
                            'to_column': id_col,
                            'confidence': overlap_ratio,
                            'description': f"{fk_col} references {id_col}"
                        })

        return relationships

    def _detect_hierarchical_relationships(self, df: pd.DataFrame, metadata: Dict[str, ColumnMetadata]) -> List[Dict[str, Any]]:
        """Detect hierarchical relationships (e.g., category -> subcategory)."""
        relationships = []

        category_columns = [col for col, meta in metadata.items() if meta.purpose == ColumnPurpose.CATEGORY]

        # Look for parent-child relationships in category columns
        for i, parent_col in enumerate(category_columns):
            for child_col in category_columns[i+1:]:
                # Check if child categories are subsets of parent categories
                parent_child_mapping = df.groupby(parent_col)[child_col].nunique()

                # If each parent has multiple children, it might be hierarchical
                if (parent_child_mapping > 1).any():
                    avg_children = parent_child_mapping.mean()
                    if avg_children > 1.5:  # On average, each parent has multiple children
                        relationships.append({
                            'type': RelationshipType.HIERARCHICAL,
                            'from_column': parent_col,
                            'to_column': child_col,
                            'confidence': min(avg_children / 10.0, 1.0),
                            'description': f"{child_col} is a subcategory of {parent_col}"
                        })

        return relationships

    def _detect_functional_dependencies(self, df: pd.DataFrame, metadata: Dict[str, ColumnMetadata]) -> List[Dict[str, Any]]:
        """Detect functional dependencies between columns."""
        relationships = []

        columns = list(df.columns)

        for i, col_a in enumerate(columns):
            for col_b in columns[i+1:]:
                # Check if col_a determines col_b (col_a -> col_b)
                dependency_strength = self._calculate_dependency_strength(df, col_a, col_b)

                if dependency_strength > 0.8:  # Strong dependency threshold
                    relationships.append({
                        'type': RelationshipType.FUNCTIONAL_DEPENDENCY,
                        'from_column': col_a,
                        'to_column': col_b,
                        'confidence': dependency_strength,
                        'description': f"{col_a} functionally determines {col_b}"
                    })

        return relationships

    def _calculate_dependency_strength(self, df: pd.DataFrame, col_a: str, col_b: str) -> float:
        """Calculate strength of functional dependency col_a -> col_b."""
        try:
            # Group by col_a and check uniqueness of col_b values
            grouped = df.groupby(col_a)[col_b].nunique()

            # If col_a determines col_b, each value of col_a should have exactly one value of col_b
            perfect_dependencies = (grouped == 1).sum()
            total_groups = len(grouped)

            if total_groups == 0:
                return 0.0

            return perfect_dependencies / total_groups
        except:
            return 0.0


class MetadataExtractor(MetadataInterface):
    """Main metadata extraction service that coordinates all extraction activities."""

    def __init__(self, context: Optional[MetadataContext] = None):
        super().__init__(context)
        self.purpose_detector = ColumnPurposeDetector()
        self.business_inferencer = BusinessContextInferencer()
        self.relationship_mapper = RelationshipMapper()

    async def extract_metadata(self, data: Any, **kwargs) -> MetadataExtractionResult:
        """
        Extract comprehensive metadata from data source.

        Args:
            data: Data to extract metadata from (DataFrame or path to data)
            **kwargs: Additional extraction options

        Returns:
            MetadataExtractionResult with comprehensive metadata
        """
        try:
            start_time = datetime.utcnow()

            # Convert data to DataFrame if needed
            if isinstance(data, str):
                # Assume it's a file path
                if data.endswith('.csv'):
                    df = pd.read_csv(data)
                elif data.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(data)
                else:
                    raise ValueError(f"Unsupported file type: {data}")
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")

            # Extract column metadata
            column_metadata = {}
            for column in df.columns:
                col_meta = await self._extract_column_metadata(column, df[column])
                column_metadata[column] = col_meta

            # Infer business domain
            business_domain, domain_confidence = self.business_inferencer.infer_business_domain(list(df.columns))

            # Detect relationships
            relationships = self.relationship_mapper.detect_relationships(df, column_metadata)

            # Identify keys
            primary_keys, foreign_keys = self._identify_keys(column_metadata, relationships)

            # Calculate dataset-level metrics
            completeness = self._calculate_dataset_completeness(df)
            quality_score = self._calculate_dataset_quality_score(column_metadata)

            # Create dataset metadata
            dataset_metadata = DatasetMetadata(
                name=kwargs.get('name', 'Extracted Dataset'),
                description=kwargs.get('description'),
                columns=column_metadata,
                total_rows=len(df),
                total_columns=len(df.columns),
                completeness=completeness,
                quality_score=quality_score,
                relationships=relationships,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
                business_domain=business_domain
            )

            # Add lineage
            lineage = MetadataLineage(
                source_id=kwargs.get('source_id', 'unknown'),
                operation='automatic_extraction',
                created_by=self.context.user_id,
                parent_lineage_id=None,
                confidence_score=domain_confidence
            )
            dataset_metadata.lineage.append(lineage)

            # Calculate performance metrics
            end_time = datetime.utcnow()
            performance_metrics = {
                'extraction_time_ms': (end_time - start_time).total_seconds() * 1000,
                'rows_processed': len(df),
                'columns_processed': len(df.columns),
                'metadata_items_extracted': len(column_metadata)
            }

            return MetadataExtractionResult(
                success=True,
                dataset_metadata=dataset_metadata,
                performance_metrics=performance_metrics,
                recommendations=self._generate_recommendations(dataset_metadata)
            )

        except Exception as e:
            return MetadataExtractionResult(
                success=False,
                dataset_metadata=None,
                errors=[str(e)]
            )

    async def _extract_column_metadata(self, column_name: str, series: pd.Series) -> ColumnMetadata:
        """Extract metadata for a single column."""
        # Detect purpose
        purpose, confidence = self.purpose_detector.detect_purpose(column_name, series)

        # Calculate statistics
        null_count = series.isnull().sum()
        unique_count = series.nunique()
        completeness = (len(series) - null_count) / len(series) if len(series) > 0 else 0
        uniqueness = unique_count / len(series) if len(series) > 0 else 0

        # Detect patterns
        patterns = self._detect_patterns(series)

        # Calculate quality score
        quality_score = self._calculate_column_quality_score(series, completeness, uniqueness)

        # Generate business meaning
        column_meta = ColumnMetadata(
            column_name=column_name,
            display_name=None,
            purpose=purpose,
            data_type=str(series.dtype),
            business_meaning=None,
            description=None,
            null_count=null_count,
            unique_count=unique_count,
            completeness=completeness,
            uniqueness=uniqueness,
            patterns=patterns,
            quality_score=quality_score,
            business_domain=None,
            sensitivity_level=None,
            confidence_score=confidence
        )

        column_meta.business_meaning = self.business_inferencer.generate_business_meaning(column_meta)

        return column_meta

    def _detect_patterns(self, series: pd.Series) -> List[str]:
        """Detect common patterns in column data."""
        patterns = []

        if len(series) == 0:
            return patterns

        sample_values = series.dropna().head(100).astype(str)

        # Common patterns
        if sample_values.str.match(r'^[A-Z]{2,3}-\d{3,}$').any():
            patterns.append('alphanumeric_code')

        if sample_values.str.match(r'^\d{4}-\d{2}-\d{2}$').any():
            patterns.append('iso_date')

        if sample_values.str.match(r'^\$[\d,]+\.?\d*$').any():
            patterns.append('currency_amount')

        return patterns

    def _calculate_column_quality_score(self, series: pd.Series, completeness: float, uniqueness: float) -> float:
        """Calculate quality score for a column."""
        score = 0.0

        # Completeness contributes 40%
        score += completeness * 0.4

        # Consistency contributes 30% (based on data type consistency)
        if len(series) > 0:
            try:
                # Try to convert to appropriate type
                if series.dtype == 'object':
                    # Check string consistency
                    non_null = series.dropna()
                    if len(non_null) > 0:
                        # Check if all values follow similar patterns
                        lengths = non_null.str.len()
                        length_consistency = 1 - (lengths.std() / lengths.mean()) if lengths.mean() > 0 else 0
                        score += max(0, min(length_consistency, 1.0)) * 0.3
                else:
                    # Numeric data is generally consistent
                    score += 0.3
            except:
                pass

        # Uniqueness contributes 30% (but penalize too high uniqueness for some purposes)
        if uniqueness < 0.95:  # High uniqueness is generally good
            score += uniqueness * 0.3
        else:
            score += 0.3  # Perfect or near-perfect uniqueness gets full points

        return min(score, 1.0)

    def _calculate_dataset_completeness(self, df: pd.DataFrame) -> float:
        """Calculate overall dataset completeness."""
        if df.empty:
            return 0.0

        total_cells = df.shape[0] * df.shape[1]
        non_null_cells = df.count().sum()

        return non_null_cells / total_cells if total_cells > 0 else 0.0

    def _calculate_dataset_quality_score(self, column_metadata: Dict[str, ColumnMetadata]) -> float:
        """Calculate overall dataset quality score."""
        if not column_metadata:
            return 0.0

        total_score = sum(meta.quality_score for meta in column_metadata.values())
        return total_score / len(column_metadata)

    def _identify_keys(self, column_metadata: Dict[str, ColumnMetadata], relationships: List[Dict[str, Any]]) -> Tuple[List[str], Dict[str, str]]:
        """Identify primary and foreign keys."""
        primary_keys = []
        foreign_keys = {}

        # Identify primary keys
        for col_name, meta in column_metadata.items():
            if meta.purpose == ColumnPurpose.PRIMARY_KEY:
                primary_keys.append(col_name)
            elif meta.purpose == ColumnPurpose.ID and meta.uniqueness > 0.95:
                primary_keys.append(col_name)

        # Identify foreign keys from relationships
        for rel in relationships:
            if rel['type'] == RelationshipType.MANY_TO_ONE:
                foreign_keys[rel['from_column']] = rel['to_column']

        return primary_keys, foreign_keys

    def _generate_recommendations(self, dataset_metadata: DatasetMetadata) -> List[str]:
        """Generate recommendations for improving data quality and metadata."""
        recommendations = []

        # Check completeness
        if dataset_metadata.completeness < 0.8:
            recommendations.append(f"Dataset completeness is {dataset_metadata.completeness:.1%}. Consider addressing missing data.")

        # Check for missing primary keys
        if not dataset_metadata.primary_keys:
            recommendations.append("No primary key identified. Consider adding a unique identifier column.")

        # Check column purposes
        unknown_columns = [col for col, meta in dataset_metadata.columns.items() if meta.purpose == ColumnPurpose.UNKNOWN]
        if unknown_columns:
            recommendations.append(f"Purpose unclear for {len(unknown_columns)} columns. Consider adding business context.")

        # Check quality scores
        low_quality_columns = [col for col, meta in dataset_metadata.columns.items() if meta.quality_score < 0.6]
        if low_quality_columns:
            recommendations.append(f"Quality issues detected in {len(low_quality_columns)} columns. Review data consistency.")

        return recommendations

    async def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate extracted metadata for consistency."""
        try:
            # Basic validation
            if 'columns' not in metadata:
                return False

            if 'total_rows' not in metadata or metadata['total_rows'] < 0:
                return False

            if 'total_columns' not in metadata or metadata['total_columns'] < 0:
                return False

            # Validate column metadata
            for col_name, col_meta in metadata['columns'].items():
                if not isinstance(col_meta, dict):
                    return False

                required_fields = ['column_name', 'purpose', 'data_type', 'completeness']
                if not all(field in col_meta for field in required_fields):
                    return False

            return True

        except Exception:
            return False
