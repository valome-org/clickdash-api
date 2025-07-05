"""
Data Normalization Engine - Convert all data to common internal format
"""

import re
import uuid
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, date
import pandas as pd
import numpy as np
from enum import Enum
from pydantic import BaseModel, Field
import logging

# Suppress pandas datetime format warnings
warnings.filterwarnings('ignore', message='Could not infer format', category=UserWarning)

from .base import PipelineStage, PipelineStageType
from utils.serialization import make_json_serializable

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Standard data types for normalization"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    CATEGORICAL = "categorical"
    JSON = "json"
    UNKNOWN = "unknown"


class ColumnPurpose(Enum):
    """Purpose classification for columns"""
    ID = "id"
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    AMOUNT = "amount"
    DATE = "date"
    TIMESTAMP = "timestamp"
    CATEGORY = "category"
    DESCRIPTION = "description"
    URL = "url"
    UNKNOWN = "unknown"


class UniversalDataSchema(BaseModel):
    """Universal data schema for normalized data"""
    schema_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)

    # Column information
    columns: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    row_count: int = 0
    column_count: int = 0

    # Data types and purposes
    data_types: Dict[str, DataType] = Field(default_factory=dict)
    column_purposes: Dict[str, ColumnPurpose] = Field(default_factory=dict)

    # Relationships
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: Dict[str, str] = Field(default_factory=dict)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 0.0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            DataType: lambda v: v.value,
            ColumnPurpose: lambda v: v.value
        }


class DataNormalizationStage(PipelineStage):
    """
    Data normalization stage that converts data to universal format
    """

    def __init__(self,
                 name: str = "data_normalization",
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name, PipelineStageType.TRANSFORMATION, config)
        config = config or {}
        self.preserve_original_names = config.get("preserve_original_names", True)
        self.normalize_column_names = config.get("normalize_column_names", True)
        self.infer_data_types = config.get("infer_data_types", True)
        self.detect_relationships = config.get("detect_relationships", True)
        self.column_mapping: Dict[str, str] = {}
        self.schema: Optional[UniversalDataSchema] = None

    async def validate_inputs(self, data: pd.DataFrame) -> bool:
        """
        Validate inputs before normalization
        """
        try:
            return not data.empty and len(data.columns) > 0
        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return False

    async def execute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Execute data normalization
        """
        try:
            # Create a copy to avoid modifying original
            normalized_df = data.copy()

            # Step 1: Normalize column names
            if self.normalize_column_names:
                normalized_df = await self._normalize_column_names(normalized_df)

            # Step 2: Infer and convert data types
            if self.infer_data_types:
                normalized_df = await self._infer_and_convert_types(normalized_df)

            # Step 3: Detect column purposes
            normalized_df = await self._detect_column_purposes(normalized_df)

            # Step 4: Detect relationships
            if self.detect_relationships:
                await self._detect_relationships(normalized_df)

            # Step 5: Create universal schema
            self.schema = await self._create_universal_schema(normalized_df)

            # Step 6: Add normalization metadata
            normalized_df.attrs['normalization_id'] = str(uuid.uuid4())
            normalized_df.attrs['normalization_timestamp'] = datetime.now().isoformat()
            normalized_df.attrs['schema'] = self.schema.dict()
            normalized_df.attrs['column_mapping'] = self.column_mapping

            # Update metrics
            self.metrics.update({
                'original_columns': len(data.columns),
                'normalized_columns': len(normalized_df.columns),
                'column_mapping': self.column_mapping,
                'schema_id': self.schema.schema_id,
                'quality_score': self.schema.quality_score
            })

            return normalized_df

        except Exception as e:
            logger.error(f"Data normalization failed: {str(e)}")
            raise

    async def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names to standard format
        """
        try:
            new_columns = {}

            for col in df.columns:
                # Convert to string
                original_name = str(col)

                # Normalize the name
                normalized_name = self._normalize_name(original_name)

                # Store mapping
                new_columns[col] = normalized_name
                if self.preserve_original_names:
                    self.column_mapping[normalized_name] = original_name

            # Rename columns
            df = df.rename(columns=new_columns)

            # Handle duplicate column names
            df = self._handle_duplicate_columns(df)

            return df

        except Exception as e:
            logger.error(f"Column name normalization failed: {str(e)}")
            raise

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a single name
        """
        # Convert to lowercase
        name = name.lower()

        # Replace spaces and special characters with underscores
        name = re.sub(r'[^a-z0-9_]', '_', name)

        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = f"col_{name}"

        # Ensure it's not empty
        if not name:
            name = "unnamed_column"

        return name

    def _handle_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle duplicate column names
        """
        columns = list(df.columns)
        seen = set()
        new_columns = []

        for col in columns:
            original_col = col
            counter = 1

            while col in seen:
                col = f"{original_col}_{counter}"
                counter += 1

            seen.add(col)
            new_columns.append(col)

        df.columns = new_columns
        return df

    async def _infer_and_convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Infer and convert data types
        """
        try:
            type_converter = DataTypeConverter()

            for col in df.columns:
                # Infer data type
                inferred_type = await type_converter.infer_data_type(df[col])

                # Convert to inferred type
                df[col] = await type_converter.convert_column(df[col], inferred_type)

                # Store in schema
                if not hasattr(self, 'data_types'):
                    self.data_types = {}
                self.data_types[col] = inferred_type

            return df

        except Exception as e:
            logger.error(f"Type inference failed: {str(e)}")
            raise

    async def _detect_column_purposes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect the purpose of each column
        """
        try:
            purpose_detector = ColumnPurposeDetector()

            if not hasattr(self, 'column_purposes'):
                self.column_purposes = {}

            for col in df.columns:
                purpose = await purpose_detector.detect_purpose(col, df[col])
                self.column_purposes[col] = purpose

            return df

        except Exception as e:
            logger.error(f"Column purpose detection failed: {str(e)}")
            raise

    async def _detect_relationships(self, df: pd.DataFrame):
        """
        Detect relationships between columns
        """
        try:
            relationship_detector = RelationshipDetector()

            # Detect primary keys
            primary_keys = await relationship_detector.detect_primary_keys(df)

            # Detect foreign keys
            foreign_keys = await relationship_detector.detect_foreign_keys(df)

            # Detect functional dependencies
            relationships = await relationship_detector.detect_functional_dependencies(df)

            # Store results
            self.primary_keys = primary_keys
            self.foreign_keys = foreign_keys
            self.relationships = relationships

        except Exception as e:
            logger.error(f"Relationship detection failed: {str(e)}")
            # Don't raise - relationships are optional

    async def _create_universal_schema(self, df: pd.DataFrame) -> UniversalDataSchema:
        """
        Create universal data schema
        """
        try:
            # Column information
            columns = {}
            for col in df.columns:
                columns[col] = {
                    'original_name': self.column_mapping.get(col, col),
                    'data_type': getattr(self, 'data_types', {}).get(col, DataType.UNKNOWN).value,
                    'purpose': getattr(self, 'column_purposes', {}).get(col, ColumnPurpose.UNKNOWN).value,
                    'nullable': df[col].isnull().any(),
                    'unique_values': df[col].nunique(),
                    'missing_count': df[col].isnull().sum(),
                    'sample_values': df[col].dropna().head(5).tolist()
                }

            # Calculate quality score
            quality_score = await self._calculate_quality_score(df)

            schema = UniversalDataSchema(
                columns=columns,
                row_count=len(df),
                column_count=len(df.columns),
                data_types=getattr(self, 'data_types', {}),
                column_purposes=getattr(self, 'column_purposes', {}),
                primary_keys=getattr(self, 'primary_keys', []),
                foreign_keys=getattr(self, 'foreign_keys', {}),
                relationships=getattr(self, 'relationships', []),
                quality_score=quality_score,
                metadata={
                    'normalization_timestamp': datetime.now().isoformat(),
                    'column_mapping': self.column_mapping,
                    'original_column_count': len(self.column_mapping) if self.column_mapping else len(df.columns)
                }
            )

            return schema

        except Exception as e:
            logger.error(f"Schema creation failed: {str(e)}")
            raise

    async def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data quality score after normalization
        """
        try:
            total_score = 0
            factors = 0

            # Type consistency (30%)
            type_consistency = sum(1 for col in df.columns if not df[col].dtype == 'object') / len(df.columns)
            total_score += type_consistency * 30
            factors += 30

            # Completeness (25%)
            completeness = (df.size - df.isnull().sum().sum()) / df.size
            total_score += completeness * 25
            factors += 25

            # Uniqueness (20%)
            uniqueness = sum(1 for col in df.columns if df[col].nunique() > 1) / len(df.columns)
            total_score += uniqueness * 20
            factors += 20

            # Column naming consistency (15%)
            naming_consistency = sum(1 for col in df.columns if col.islower() and '_' in col or col.islower()) / len(df.columns)
            total_score += naming_consistency * 15
            factors += 15

            # Relationship detection (10%)
            relationship_score = 1 if hasattr(self, 'primary_keys') and self.primary_keys else 0.5
            total_score += relationship_score * 10
            factors += 10

            return round(total_score, 2)

        except Exception as e:
            logger.error(f"Quality score calculation failed: {str(e)}")
            return 0.0


class DataTypeConverter:
    """
    Convert data types to standard formats
    """

    async def infer_data_type(self, series: pd.Series) -> DataType:
        """
        Infer data type from pandas series
        """
        try:
            # Remove null values for analysis
            non_null_series = series.dropna()

            if len(non_null_series) == 0:
                return DataType.UNKNOWN

            # Check for boolean
            if await self._is_boolean(non_null_series):
                return DataType.BOOLEAN

            # Check for datetime
            if await self._is_datetime(non_null_series):
                return DataType.DATETIME

            # Check for date
            if await self._is_date(non_null_series):
                return DataType.DATE

            # Check for integer
            if await self._is_integer(non_null_series):
                return DataType.INTEGER

            # Check for float
            if await self._is_float(non_null_series):
                return DataType.FLOAT

            # Check for categorical
            if await self._is_categorical(non_null_series):
                return DataType.CATEGORICAL

            # Default to string
            return DataType.STRING

        except Exception as e:
            logger.error(f"Data type inference failed: {str(e)}")
            return DataType.UNKNOWN

    async def _is_boolean(self, series: pd.Series) -> bool:
        """Check if series represents boolean values"""
        if series.dtype == 'bool':
            return True

        # Check for boolean-like strings
        unique_values = set(str(v).lower() for v in series.unique())
        bool_values = {'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}

        return unique_values.issubset(bool_values) and len(unique_values) <= 2

    async def _is_datetime(self, series: pd.Series) -> bool:
        """Check if series represents datetime values"""
        if pd.api.types.is_datetime64_any_dtype(series):
            return True

        try:
            # Sample data for testing
            sample_data = series.dropna().head(50)
            if len(sample_data) == 0:
                return False

            # Try to parse as datetime without format inference warnings
            parsed = pd.to_datetime(sample_data, errors='coerce')

            # Check if most values were successfully parsed
            success_rate = parsed.notna().sum() / len(parsed)
            return success_rate > 0.7  # At least 70% success rate
        except:
            return False

    async def _is_date(self, series: pd.Series) -> bool:
        """Check if series represents date values"""
        try:
            # Sample data for testing
            sample_data = series.dropna().head(50)
            if len(sample_data) == 0:
                return False

            # Try to parse as datetime
            parsed = pd.to_datetime(sample_data, errors='coerce')

            # Filter out failed conversions
            valid_parsed = parsed.dropna()
            if len(valid_parsed) == 0:
                return False

            # Check if most values have time component at midnight (indicating date-only)
            midnight_count = sum(1 for t in valid_parsed if t.time() == pd.Timestamp('00:00:00').time())
            return midnight_count / len(valid_parsed) > 0.8  # 80% are date-only
        except:
            return False

    async def _is_integer(self, series: pd.Series) -> bool:
        """Check if series represents integer values"""
        if pd.api.types.is_integer_dtype(series):
            return True

        try:
            # Try to convert to numeric
            numeric = pd.to_numeric(series, errors='raise')
            # Check if all values are integers
            return all(float(v).is_integer() for v in numeric)
        except:
            return False

    async def _is_float(self, series: pd.Series) -> bool:
        """Check if series represents float values"""
        if pd.api.types.is_numeric_dtype(series):
            return True

        try:
            pd.to_numeric(series, errors='raise')
            return True
        except:
            return False

    async def _is_categorical(self, series: pd.Series) -> bool:
        """Check if series represents categorical values"""
        # If unique values are less than 5% of total, consider categorical
        unique_ratio = series.nunique() / len(series)
        return unique_ratio < 0.05 and series.nunique() > 1

    async def convert_column(self, series: pd.Series, target_type: DataType) -> pd.Series:
        """
        Convert series to target data type
        """
        try:
            if target_type == DataType.BOOLEAN:
                return await self._convert_to_boolean(series)
            elif target_type == DataType.INTEGER:
                return await self._convert_to_integer(series)
            elif target_type == DataType.FLOAT:
                return await self._convert_to_float(series)
            elif target_type == DataType.DATETIME:
                return await self._convert_to_datetime(series)
            elif target_type == DataType.DATE:
                return await self._convert_to_date(series)
            elif target_type == DataType.CATEGORICAL:
                return await self._convert_to_categorical(series)
            else:
                return await self._convert_to_string(series)

        except Exception as e:
            logger.warning(f"Type conversion failed for {target_type}: {str(e)}")
            return series  # Return original if conversion fails

    async def _convert_to_boolean(self, series: pd.Series) -> pd.Series:
        """Convert to boolean"""
        def convert_value(val):
            if pd.isna(val):
                return val
            str_val = str(val).lower()
            if str_val in ['true', 'yes', '1', 'y']:
                return True
            elif str_val in ['false', 'no', '0', 'n']:
                return False
            else:
                return val

        return series.apply(convert_value)

    async def _convert_to_integer(self, series: pd.Series) -> pd.Series:
        """Convert to integer"""
        return pd.to_numeric(series, errors='coerce').astype('Int64')

    async def _convert_to_float(self, series: pd.Series) -> pd.Series:
        """Convert to float"""
        return pd.to_numeric(series, errors='coerce')

    async def _convert_to_datetime(self, series: pd.Series) -> pd.Series:
        """Convert to datetime"""
        return pd.to_datetime(series, errors='coerce')

    async def _convert_to_date(self, series: pd.Series) -> pd.Series:
        """Convert to date"""
        return pd.to_datetime(series, errors='coerce').dt.date

    async def _convert_to_categorical(self, series: pd.Series) -> pd.Series:
        """Convert to categorical"""
        return series.astype('category')

    async def _convert_to_string(self, series: pd.Series) -> pd.Series:
        """Convert to string"""
        return series.astype('string')


class ColumnPurposeDetector:
    """
    Detect the purpose of columns based on content and name
    """

    def __init__(self):
        self.patterns = {
            ColumnPurpose.ID: [
                r'.*id$', r'.*_id$', r'^id_.*', r'identifier', r'key', r'.*key$'
            ],
            ColumnPurpose.NAME: [
                r'.*name.*', r'.*title.*', r'.*label.*', r'first.*name', r'last.*name'
            ],
            ColumnPurpose.EMAIL: [
                r'.*email.*', r'.*mail.*', r'.*e_mail.*'
            ],
            ColumnPurpose.PHONE: [
                r'.*phone.*', r'.*tel.*', r'.*mobile.*', r'.*cell.*'
            ],
            ColumnPurpose.ADDRESS: [
                r'.*address.*', r'.*street.*', r'.*city.*', r'.*state.*', r'.*zip.*'
            ],
            ColumnPurpose.AMOUNT: [
                r'.*amount.*', r'.*price.*', r'.*cost.*', r'.*value.*', r'.*total.*'
            ],
            ColumnPurpose.DATE: [
                r'.*date.*', r'.*time.*', r'.*created.*', r'.*modified.*', r'.*updated.*'
            ],
            ColumnPurpose.CATEGORY: [
                r'.*category.*', r'.*type.*', r'.*status.*', r'.*group.*', r'.*class.*'
            ],
            ColumnPurpose.DESCRIPTION: [
                r'.*desc.*', r'.*comment.*', r'.*note.*', r'.*remark.*'
            ],
            ColumnPurpose.URL: [
                r'.*url.*', r'.*link.*', r'.*href.*', r'.*website.*'
            ]
        }

    async def detect_purpose(self, column_name: str, series: pd.Series) -> ColumnPurpose:
        """
        Detect column purpose based on name and content
        """
        try:
            # Check name patterns
            purpose_from_name = await self._detect_from_name(column_name.lower())

            # Check content patterns
            purpose_from_content = await self._detect_from_content(series)

            # Combine results (name takes precedence)
            if purpose_from_name != ColumnPurpose.UNKNOWN:
                return purpose_from_name
            elif purpose_from_content != ColumnPurpose.UNKNOWN:
                return purpose_from_content
            else:
                return ColumnPurpose.UNKNOWN

        except Exception as e:
            logger.error(f"Purpose detection failed: {str(e)}")
            return ColumnPurpose.UNKNOWN

    async def _detect_from_name(self, name: str) -> ColumnPurpose:
        """Detect purpose from column name"""
        for purpose, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    return purpose
        return ColumnPurpose.UNKNOWN

    async def _detect_from_content(self, series: pd.Series) -> ColumnPurpose:
        """Detect purpose from column content"""
        non_null_series = series.dropna()

        if len(non_null_series) == 0:
            return ColumnPurpose.UNKNOWN

        # Sample some values for analysis
        sample_values = non_null_series.head(100).astype(str)

        # Check for email pattern
        if any('@' in val and '.' in val for val in sample_values):
            return ColumnPurpose.EMAIL

        # Check for URL pattern
        if any(val.startswith(('http://', 'https://', 'www.')) for val in sample_values):
            return ColumnPurpose.URL

        # Check for phone pattern
        phone_pattern = r'[\+]?[1-9]?[\-.\s]?\(?[0-9]{3}\)?[\-.\s]?[0-9]{3}[\-.\s]?[0-9]{4}'
        if any(re.match(phone_pattern, val) for val in sample_values):
            return ColumnPurpose.PHONE

        return ColumnPurpose.UNKNOWN


class RelationshipDetector:
    """
    Detect relationships between columns
    """

    async def detect_primary_keys(self, df: pd.DataFrame) -> List[str]:
        """
        Detect potential primary key columns
        """
        try:
            primary_keys = []

            for col in df.columns:
                # Check if column has unique values
                if df[col].nunique() == len(df) and df[col].nunique() > 1:
                    # Check if it looks like an ID column
                    if self._looks_like_id_column(col, df[col]):
                        primary_keys.append(col)

            return primary_keys

        except Exception as e:
            logger.error(f"Primary key detection failed: {str(e)}")
            return []

    async def detect_foreign_keys(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Detect potential foreign key relationships
        """
        try:
            foreign_keys = {}

            # This is a simplified implementation
            # In a real system, you'd compare with other tables
            for col in df.columns:
                if col.endswith('_id') and col != 'id':
                    # Assume it's a foreign key to another table
                    referenced_table = col.replace('_id', '')
                    foreign_keys[col] = referenced_table

            return foreign_keys

        except Exception as e:
            logger.error(f"Foreign key detection failed: {str(e)}")
            return {}

    async def detect_functional_dependencies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect functional dependencies between columns
        """
        try:
            relationships = []

            for col1 in df.columns:
                for col2 in df.columns:
                    if col1 != col2:
                        # Check if col1 determines col2
                        if self._is_functional_dependency(df, col1, col2):
                            relationships.append({
                                'type': 'functional_dependency',
                                'determinant': col1,
                                'dependent': col2,
                                'strength': self._calculate_dependency_strength(df, col1, col2)
                            })

            return relationships

        except Exception as e:
            logger.error(f"Functional dependency detection failed: {str(e)}")
            return []

    def _looks_like_id_column(self, col_name: str, series: pd.Series) -> bool:
        """Check if column looks like an ID column"""
        # Check name patterns
        if re.search(r'.*id$|^id.*|.*key$|^key.*', col_name.lower()):
            return True

        # Check if values are sequential integers
        if pd.api.types.is_integer_dtype(series):
            sorted_values = sorted(series.dropna().unique())
            if len(sorted_values) > 1:
                return all(sorted_values[i] == sorted_values[i-1] + 1 for i in range(1, len(sorted_values)))

        return False

    def _is_functional_dependency(self, df: pd.DataFrame, col1: str, col2: str) -> bool:
        """Check if col1 functionally determines col2"""
        try:
            # Group by col1 and check if each group has only one unique value in col2
            grouped = df.groupby(col1)[col2].nunique()
            return all(count == 1 for count in grouped)
        except:
            return False

    def _calculate_dependency_strength(self, df: pd.DataFrame, col1: str, col2: str) -> float:
        """Calculate strength of functional dependency"""
        try:
            # Simple measure: ratio of unique col1 values to total rows
            return df[col1].nunique() / len(df)
        except:
            return 0.0
