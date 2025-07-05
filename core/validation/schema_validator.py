"""
Schema validation and evolution tracking for data validation.

This module provides comprehensive schema validation capabilities including:
- Schema definition and validation
- Schema evolution tracking over time
- Schema compatibility checking
- Migration support for schema changes
"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from enum import Enum
import pandas as pd
from pydantic import BaseModel, Field
import uuid

from .base import ValidatorInterface, ValidationResult, ValidationIssue, ValidationSeverity


class DataType(str, Enum):
    """Supported data types for schema validation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"


class ColumnConstraint(BaseModel):
    """Constraints for a single column."""

    not_null: bool = Field(default=False, description="Column cannot be null")
    unique: bool = Field(default=False, description="Column values must be unique")
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum allowed value")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum allowed value")
    min_length: Optional[int] = Field(None, description="Minimum string length")
    max_length: Optional[int] = Field(None, description="Maximum string length")
    regex_pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    allowed_values: Optional[List[Any]] = Field(None, description="List of allowed values")
    custom_rules: Dict[str, Any] = Field(default_factory=dict, description="Custom validation rules")


class ColumnSchema(BaseModel):
    """Schema definition for a single column."""

    name: str = Field(..., description="Column name")
    data_type: DataType = Field(..., description="Expected data type")
    nullable: bool = Field(default=True, description="Whether column can contain null values")
    constraints: ColumnConstraint = Field(default_factory=lambda: ColumnConstraint(min_value=None, max_value=None, min_length=None, max_length=None, regex_pattern=None, allowed_values=None), description="Column constraints")
    description: Optional[str] = Field(None, description="Human-readable description")
    business_meaning: Optional[str] = Field(None, description="Business context/meaning")
    tags: Set[str] = Field(default_factory=set, description="Tags for categorization")


class Schema(BaseModel):
    """Complete schema definition for a dataset."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique schema identifier")
    name: str = Field(..., description="Schema name")
    version: str = Field(default="1.0.0", description="Schema version")
    columns: List[ColumnSchema] = Field(..., description="Column definitions")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Schema creation timestamp")
    created_by: Optional[str] = Field(None, description="Schema creator")
    description: Optional[str] = Field(None, description="Schema description")
    tags: Set[str] = Field(default_factory=set, description="Schema tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_column_by_name(self, name: str) -> Optional[ColumnSchema]:
        """Get column schema by name."""
        for column in self.columns:
            if column.name == name:
                return column
        return None

    def get_column_names(self) -> List[str]:
        """Get list of all column names."""
        return [col.name for col in self.columns]

    def calculate_hash(self) -> str:
        """Calculate hash of schema for comparison."""
        schema_data = {
            "columns": [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "nullable": col.nullable,
                    "constraints": col.constraints.dict()
                }
                for col in self.columns
            ]
        }
        return hashlib.sha256(json.dumps(schema_data, sort_keys=True).encode()).hexdigest()


class SchemaCompatibilityLevel(str, Enum):
    """Levels of schema compatibility."""
    IDENTICAL = "identical"
    FORWARD_COMPATIBLE = "forward_compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING_CHANGE = "breaking_change"


class SchemaChange(BaseModel):
    """Represents a change between two schemas."""

    change_type: str = Field(..., description="Type of change")
    field: str = Field(..., description="Field that changed")
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Optional[Any] = Field(None, description="New value")
    description: str = Field(..., description="Human-readable description")
    impact: str = Field(..., description="Impact of the change")
    compatibility_level: SchemaCompatibilityLevel = Field(..., description="Compatibility level")


class SchemaValidationResult(ValidationResult):
    """Results of schema validation with additional schema-specific information."""

    schema_id: Optional[str] = Field(None, description="ID of schema used for validation")
    detected_schema: Optional[Schema] = Field(None, description="Auto-detected schema from data")
    compatibility_level: Optional[SchemaCompatibilityLevel] = Field(None, description="Compatibility level")
    suggested_migrations: List[str] = Field(default_factory=list, description="Suggested migration steps")


class SchemaEvolutionRecord(BaseModel):
    """Record of schema evolution over time."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Evolution record ID")
    schema_name: str = Field(..., description="Name of the schema")
    from_version: Optional[str] = Field(None, description="Previous version")
    to_version: str = Field(..., description="New version")
    changes: List[SchemaChange] = Field(..., description="List of changes")
    migration_script: Optional[str] = Field(None, description="Migration script")
    applied_at: datetime = Field(default_factory=datetime.utcnow, description="When migration was applied")
    applied_by: Optional[str] = Field(None, description="Who applied the migration")


class SchemaValidator(ValidatorInterface):
    """Main schema validator with evolution tracking capabilities."""

    def __init__(self):
        self.schemas: Dict[str, Schema] = {}
        self.evolution_history: List[SchemaEvolutionRecord] = []

    async def validate(self, data: pd.DataFrame, schema: Optional[Schema] = None, **kwargs) -> SchemaValidationResult:
        """
        Validate data against a schema.

        Args:
            data: DataFrame to validate
            schema: Schema to validate against (if None, will auto-detect)
            **kwargs: Additional validation parameters

        Returns:
            SchemaValidationResult with validation outcome
        """
        start_time = datetime.utcnow()

        result = SchemaValidationResult(
            is_valid=True,
            execution_time_ms=0,
            schema_id=schema.id if schema else None
        ,
            detected_schema=None,
            compatibility_level=None
        )

        # Auto-detect schema if not provided
        if schema is None:
            schema = await self._detect_schema(data)
            result.detected_schema = schema

        # Validate columns
        await self._validate_columns(data, schema, result)

        # Validate data types
        await self._validate_data_types(data, schema, result)

        # Validate constraints
        await self._validate_constraints(data, schema, result)

        # Calculate execution time
        end_time = datetime.utcnow()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return result

    async def _detect_schema(self, data: pd.DataFrame) -> Schema:
        """Auto-detect schema from DataFrame."""
        columns = []

        for col_name in data.columns:
            col_data = data[col_name]

            # Detect data type
            data_type = self._infer_data_type(col_data)

            # Check if nullable
            nullable = col_data.isnull().any()

            # Create column schema
            column = ColumnSchema(
                name=col_name,
                data_type=data_type,
                nullable=nullable
            ,
                description=None,
                business_meaning=None
            )

            columns.append(column)

        return Schema(
            name="auto_detected",
            columns=columns,
            description="Auto-detected schema from data",
            created_by=None
        )

    def _infer_data_type(self, series: pd.Series) -> DataType:
        """Infer data type from pandas Series."""
        # Remove null values for type inference
        non_null_series = series.dropna()

        if len(non_null_series) == 0:
            return DataType.UNKNOWN

        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return DataType.DATETIME

        # Check for boolean
        if pd.api.types.is_bool_dtype(series):
            return DataType.BOOLEAN

        # Check for integer
        if pd.api.types.is_integer_dtype(series):
            return DataType.INTEGER

        # Check for float
        if pd.api.types.is_float_dtype(series):
            return DataType.FLOAT

        # Check if string can be datetime
        if pd.api.types.is_string_dtype(series):
            try:
                pd.to_datetime(non_null_series.head(100))
                return DataType.DATETIME
            except:
                pass

            # Check if categorical (low unique values)
            unique_ratio = len(non_null_series.unique()) / len(non_null_series)
            if unique_ratio < 0.1 and len(non_null_series.unique()) < 50:
                return DataType.CATEGORICAL

        return DataType.STRING

    async def _validate_columns(self, data: pd.DataFrame, schema: Schema, result: SchemaValidationResult):
        """Validate that all required columns are present."""
        data_columns = set(data.columns)
        schema_columns = set(schema.get_column_names())

        # Check for missing columns
        missing_columns = schema_columns - data_columns
        for col in missing_columns:
            col_schema = schema.get_column_by_name(col)
            if col_schema and not col_schema.nullable:
                result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Required column '{col}' is missing",
                    field=col,
                    row=None,
                    value=None,
                    suggested_fix=f"Add column '{col}' to the dataset"

                ))

        # Check for extra columns
        extra_columns = data_columns - schema_columns
        for col in extra_columns:
            result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.WARNING,
                    message=f"Unexpected column '{col}' found",
                    field=col,
                    row=None,
                    value=None,
                    suggested_fix=f"Remove column '{col}' or update schema to include it"

                ))

    async def _validate_data_types(self, data: pd.DataFrame, schema: Schema, result: SchemaValidationResult):
        """Validate data types match schema expectations."""
        for column in schema.columns:
            if column.name not in data.columns:
                continue

            col_data = data[column.name]
            expected_type = column.data_type

            # Skip validation for unknown types
            if expected_type == DataType.UNKNOWN:
                continue

            # Check type compatibility
            if not self._is_type_compatible(col_data, expected_type):
                result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{column.name}' has incompatible data type. Expected {expected_type}, but found different type",
                    field=column.name,
                    row=None,
                    value=None,
                    suggested_fix=f"Convert column '{column.name}' to {expected_type} type"
                ))

    def _is_type_compatible(self, series: pd.Series, expected_type: DataType) -> bool:
        """Check if series data type is compatible with expected type."""
        non_null_series = series.dropna()

        if len(non_null_series) == 0:
            return True

        if expected_type == DataType.STRING:
            return True  # Most types can be converted to string
        elif expected_type == DataType.INTEGER:
            return pd.api.types.is_integer_dtype(series)
        elif expected_type == DataType.FLOAT:
            return pd.api.types.is_numeric_dtype(series)
        elif expected_type == DataType.BOOLEAN:
            return pd.api.types.is_bool_dtype(series)
        elif expected_type == DataType.DATETIME:
            if pd.api.types.is_datetime64_any_dtype(series):
                return True
            # Try to parse as datetime
            try:
                pd.to_datetime(non_null_series.head(100))
                return True
            except:
                return False

        return False

    async def _validate_constraints(self, data: pd.DataFrame, schema: Schema, result: SchemaValidationResult):
        """Validate data against column constraints."""
        for column in schema.columns:
            if column.name not in data.columns:
                continue

            col_data = data[column.name]
            constraints = column.constraints

            # Check not_null constraint
            if constraints.not_null and col_data.isnull().any():
                null_count = col_data.isnull().sum()
                result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{column.name}' has {null_count} null values but is marked as not_null",
                    field=column.name,
                    row=None,
                    value=None,
                    suggested_fix=f"Remove null values from column '{column.name}' or update constraint"

                ))

            # Check unique constraint
            if constraints.unique and col_data.duplicated().any():
                duplicate_count = col_data.duplicated().sum()
                result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{column.name}' has {duplicate_count} duplicate values but is marked as unique",
                    field=column.name,
                    row=None,
                    value=None,
                    suggested_fix=f"Remove duplicate values from column '{column.name}'"

                ))

            # Check min/max values for numeric columns
            if column.data_type in [DataType.INTEGER, DataType.FLOAT]:
                numeric_data = pd.to_numeric(col_data, errors='coerce').dropna()

                if constraints.min_value is not None and (numeric_data < constraints.min_value).any():
                    violation_count = (numeric_data < constraints.min_value).sum()
                    result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{column.name}' has {violation_count} values below minimum ({constraints.min_value})",
                    field=column.name,
                    row=None,
                    value=None,
                    suggested_fix=f"Ensure all values in '{column.name}' are >= {constraints.min_value}"

                ))

                if constraints.max_value is not None and (numeric_data > constraints.max_value).any():
                    violation_count = (numeric_data > constraints.max_value).sum()
                    result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Column '{column.name}' has {violation_count} values above maximum ({constraints.max_value})",
                    field=column.name,
                    row=None,
                    value=None,
                    suggested_fix=f"Ensure all values in '{column.name}' are <= {constraints.max_value}"

                ))

    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this validator."""
        return {
            "name": "SchemaValidator",
            "version": "1.0.0",
            "description": "Validates data against defined schemas with evolution tracking",
            "supported_features": [
                "Column validation",
                "Data type validation",
                "Constraint validation",
                "Schema evolution tracking",
                "Auto-schema detection"
            ]
        }


class SchemaEvolutionTracker:
    """Tracks schema evolution and manages version history."""

    def __init__(self):
        self.schemas: Dict[str, Dict[str, Schema]] = {}  # schema_name -> version -> schema
        self.evolution_records: List[SchemaEvolutionRecord] = []

    def register_schema(self, schema: Schema) -> None:
        """Register a new schema version."""
        if schema.name not in self.schemas:
            self.schemas[schema.name] = {}

        self.schemas[schema.name][schema.version] = schema

    def get_schema(self, name: str, version: Optional[str] = None) -> Optional[Schema]:
        """Get schema by name and version (latest if version not specified)."""
        if name not in self.schemas:
            return None

        if version is None:
            # Get latest version
            versions = list(self.schemas[name].keys())
            if not versions:
                return None
            # Simple string comparison for version (assumes semantic versioning)
            latest_version = max(versions)
            return self.schemas[name][latest_version]

        return self.schemas[name].get(version)

    def compare_schemas(self, old_schema: Schema, new_schema: Schema) -> List[SchemaChange]:
        """Compare two schemas and identify changes."""
        changes = []

        old_columns = {col.name: col for col in old_schema.columns}
        new_columns = {col.name: col for col in new_schema.columns}

        # Check for removed columns
        for col_name in old_columns:
            if col_name not in new_columns:
                changes.append(SchemaChange(
                    change_type="column_removed",
                    field=col_name,
                    old_value=old_columns[col_name].dict(),
                    new_value=None,
                    description=f"Column '{col_name}' was removed",
                    impact="Data loss possible",
                    compatibility_level=SchemaCompatibilityLevel.BREAKING_CHANGE
                ))

        # Check for added columns
        for col_name in new_columns:
            if col_name not in old_columns:
                changes.append(SchemaChange(
                    change_type="column_added",
                    field=col_name,
                    old_value=None,
                    new_value=new_columns[col_name].dict(),
                    description=f"Column '{col_name}' was added",
                    impact="Forward compatible",
                    compatibility_level=SchemaCompatibilityLevel.FORWARD_COMPATIBLE
                ))

        # Check for modified columns
        for col_name in old_columns:
            if col_name in new_columns:
                old_col = old_columns[col_name]
                new_col = new_columns[col_name]

                # Check data type changes
                if old_col.data_type != new_col.data_type:
                    compatibility = self._assess_type_change_compatibility(old_col.data_type, new_col.data_type)
                    changes.append(SchemaChange(
                        change_type="data_type_changed",
                        field=col_name,
                        old_value=old_col.data_type,
                        new_value=new_col.data_type,
                        description=f"Column '{col_name}' data type changed from {old_col.data_type} to {new_col.data_type}",
                        impact="Type conversion required",
                        compatibility_level=compatibility
                    ))

                # Check nullable changes
                if old_col.nullable != new_col.nullable:
                    compatibility = SchemaCompatibilityLevel.BREAKING_CHANGE if new_col.nullable == False else SchemaCompatibilityLevel.BACKWARD_COMPATIBLE
                    changes.append(SchemaChange(
                        change_type="nullable_changed",
                        field=col_name,
                        old_value=old_col.nullable,
                        new_value=new_col.nullable,
                        description=f"Column '{col_name}' nullable changed from {old_col.nullable} to {new_col.nullable}",
                        impact="Constraint change",
                        compatibility_level=compatibility
                    ))

        return changes

    def _assess_type_change_compatibility(self, old_type: DataType, new_type: DataType) -> SchemaCompatibilityLevel:
        """Assess compatibility level for data type changes."""
        # Define compatible type transitions
        compatible_transitions = {
            DataType.INTEGER: [DataType.FLOAT, DataType.STRING],
            DataType.FLOAT: [DataType.STRING],
            DataType.BOOLEAN: [DataType.STRING],
            DataType.DATE: [DataType.DATETIME, DataType.STRING],
            DataType.DATETIME: [DataType.STRING],
            DataType.CATEGORICAL: [DataType.STRING]
        }

        if old_type == new_type:
            return SchemaCompatibilityLevel.IDENTICAL

        if old_type in compatible_transitions and new_type in compatible_transitions[old_type]:
            return SchemaCompatibilityLevel.FORWARD_COMPATIBLE

        return SchemaCompatibilityLevel.BREAKING_CHANGE

    def track_evolution(self, old_schema: Schema, new_schema: Schema, migration_script: Optional[str] = None) -> SchemaEvolutionRecord:
        """Track schema evolution from old to new version."""
        changes = self.compare_schemas(old_schema, new_schema)

        record = SchemaEvolutionRecord(
            schema_name=new_schema.name,
            from_version=old_schema.version,
            to_version=new_schema.version,
            changes=changes,
            migration_script=migration_script
        ,
            applied_by=None
        )

        self.evolution_records.append(record)
        return record


class SchemaCompatibilityChecker:
    """Checks compatibility between different schema versions."""

    @staticmethod
    def check_compatibility(old_schema: Schema, new_schema: Schema) -> Tuple[SchemaCompatibilityLevel, List[str]]:
        """
        Check compatibility between two schemas.

        Returns:
            Tuple of (compatibility_level, list_of_issues)
        """
        tracker = SchemaEvolutionTracker()
        changes = tracker.compare_schemas(old_schema, new_schema)

        if not changes:
            return SchemaCompatibilityLevel.IDENTICAL, []

        # Determine overall compatibility level
        breaking_changes = [c for c in changes if c.compatibility_level == SchemaCompatibilityLevel.BREAKING_CHANGE]

        if breaking_changes:
            issues = [f"{change.description} - {change.impact}" for change in breaking_changes]
            return SchemaCompatibilityLevel.BREAKING_CHANGE, issues

        forward_incompatible = [c for c in changes if c.compatibility_level == SchemaCompatibilityLevel.FORWARD_COMPATIBLE]
        if forward_incompatible:
            issues = [f"{change.description} - {change.impact}" for change in forward_incompatible]
            return SchemaCompatibilityLevel.FORWARD_COMPATIBLE, issues

        backward_incompatible = [c for c in changes if c.compatibility_level == SchemaCompatibilityLevel.BACKWARD_COMPATIBLE]
        if backward_incompatible:
            issues = [f"{change.description} - {change.impact}" for change in backward_incompatible]
            return SchemaCompatibilityLevel.BACKWARD_COMPATIBLE, issues

        return SchemaCompatibilityLevel.IDENTICAL, []
