"""
API endpoints for comprehensive data validation.

This module provides REST API endpoints for:
- Schema validation and management
- Business rule validation
- Data profiling
- Validation reporting and analytics
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
import pandas as pd
import io
import json
from pydantic import BaseModel, Field

from services.validation_service import ValidationService, ValidationRequest, ValidationReport
from core.validation import (
    Schema,
    BusinessRule,
    RuleCondition,
    RuleOperator,
    LogicalOperator,
    ValidationSeverity,
    ColumnSchema,
    DataType,
    ColumnConstraint
)
from utils.serialization import make_json_serializable

# Initialize router and service
router = APIRouter(prefix="/api/validation", tags=["validation"])
validation_service = ValidationService()


# Pydantic models for API requests
class ValidateFileRequest(BaseModel):
    validation_types: List[str] = Field(default=["schema", "rules", "profile"],
                                      description="Types of validation to perform")
    schema_id: Optional[str] = Field(None, description="Specific schema to validate against")
    rule_categories: Optional[List[str]] = Field(None, description="Rule categories to apply")
    options: Dict[str, Any] = Field(default_factory=dict, description="Validation options")


class SchemaRequest(BaseModel):
    name: str = Field(..., description="Schema name")
    version: str = Field(default="1.0.0", description="Schema version")
    columns: List[Dict[str, Any]] = Field(..., description="Column definitions")
    description: Optional[str] = Field(None, description="Schema description")


class BusinessRuleRequest(BaseModel):
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    conditions: List[Dict[str, Any]] = Field(..., description="Rule conditions")
    logical_operator: str = Field(default="and", description="Logical operator")
    severity: str = Field(default="error", description="Rule severity")
    category: str = Field(default="general", description="Rule category")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix")


# Validation endpoints
@router.post("/validate-file", response_model=Dict[str, Any])
async def validate_file(
    file: UploadFile = File(...),
    request_data: str = Form(...)
):
    """
    Validate an uploaded file using comprehensive validation.

    Args:
        file: Uploaded file (CSV or Excel)
        request_data: JSON string with validation request parameters

    Returns:
        Comprehensive validation report
    """
    try:
        # Parse request data
        request_dict = json.loads(request_data)
        validate_request = ValidateFileRequest(**request_dict)

        # Read file data
        filename = file.filename or "unknown"
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel files.")

        # Create validation request
        validation_request = ValidationRequest(
            data=data,
            validation_types=validate_request.validation_types,
            schema_id=validate_request.schema_id,
            rule_categories=validate_request.rule_categories,
            context=None,
            options={**validate_request.options, "dataset_name": filename}

        )

        # Perform validation
        report = await validation_service.validate_comprehensive(validation_request)

        # Convert to safe JSON format
        return make_json_serializable(report.dict())

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/validate-data", response_model=Dict[str, Any])
async def validate_data(request: Dict[str, Any]):
    """
    Validate data provided directly in the request.

    Args:
        request: Validation request with data and parameters

    Returns:
        Comprehensive validation report
    """
    try:
        validation_request = ValidationRequest(**request)
        report = await validation_service.validate_comprehensive(validation_request)
        return make_json_serializable(report.dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Check validation service health."""
    try:
        service_info = validation_service.get_service_info()
        return {
            "status": "healthy",
            "service_info": service_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Schema management endpoints
@router.post("/schemas", response_model=Dict[str, Any])
async def create_schema(request: SchemaRequest):
    """
    Create a new data schema.

    Args:
        request: Schema definition request

    Returns:
        Created schema information
    """
    try:
        # Convert column definitions to ColumnSchema objects
        columns = []
        for col_def in request.columns:
            constraints = ColumnConstraint(**col_def.get("constraints", {}))
            column = ColumnSchema(
                name=col_def["name"],
                data_type=DataType(col_def["data_type"]),
                nullable=col_def.get("nullable", True),
                constraints=constraints,
                description=col_def.get("description"),
                business_meaning=col_def.get("business_meaning"),
                tags=set(col_def.get("tags", []))
            )
            columns.append(column)

        # Create schema
        schema = Schema(
            name=request.name,
            version=request.version,
            columns=columns,
            description=request.description
        ,
            created_by=None
        )

        # Register schema
        validation_service.register_schema(schema)

        return {
            "message": "Schema created successfully",
            "schema_id": schema.id,
            "schema": make_json_serializable(schema.dict())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema creation failed: {str(e)}")


@router.get("/schemas")
async def list_schemas():
    """List all registered schemas."""
    try:
        schemas_info = {}
        for schema_name, versions in validation_service.schema_tracker.schemas.items():
            schemas_info[schema_name] = {
                "versions": list(versions.keys()),
                "latest_version": max(versions.keys()) if versions else None
            }

        return {
            "schemas": schemas_info,
            "total_schemas": len(schemas_info)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list schemas: {str(e)}")


@router.get("/schemas/{schema_name}")
async def get_schema(schema_name: str, version: Optional[str] = None):
    """
    Get a specific schema by name and version.

    Args:
        schema_name: Name of the schema
        version: Specific version (latest if not provided)

    Returns:
        Schema definition
    """
    try:
        schema = validation_service.get_schema(schema_name, version)
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")

        return make_json_serializable(schema.dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")


@router.post("/schemas/compare")
async def compare_schemas(request: Dict[str, str]):
    """
    Compare two schemas and get compatibility information.

    Args:
        request: Dictionary with old_schema_name, old_version, new_schema_name, new_version

    Returns:
        Schema comparison results
    """
    try:
        old_schema = validation_service.get_schema(
            request["old_schema_name"],
            request.get("old_version")
        )
        new_schema = validation_service.get_schema(
            request["new_schema_name"],
            request.get("new_version")
        )

        if not old_schema or not new_schema:
            raise HTTPException(status_code=404, detail="One or both schemas not found")

        changes = validation_service.compare_schemas(old_schema, new_schema)
        compatibility = validation_service.check_schema_compatibility(old_schema, new_schema)

        return {
            "changes": changes,
            "compatibility": compatibility,
            "schemas_compared": {
                "old": f"{old_schema.name}:{old_schema.version}",
                "new": f"{new_schema.name}:{new_schema.version}"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema comparison failed: {str(e)}")


# Business rule management endpoints
@router.post("/rules", response_model=Dict[str, Any])
async def create_business_rule(request: BusinessRuleRequest):
    """
    Create a new business rule.

    Args:
        request: Business rule definition

    Returns:
        Created rule information
    """
    try:
        # Convert conditions
        conditions = []
        for cond_def in request.conditions:
            condition = RuleCondition(
                field=cond_def["field"],
                operator=RuleOperator(cond_def["operator"]),
                value=cond_def["value"],
                case_sensitive=cond_def.get("case_sensitive", True)
            )
            conditions.append(condition)

        # Create business rule
        rule = BusinessRule(
            name=request.name,
            description=request.description,
            conditions=conditions,
            logical_operator=LogicalOperator(request.logical_operator),
            severity=ValidationSeverity(request.severity),
            category=request.category,
            suggested_fix=request.suggested_fix
        ,
            created_by=None,
            custom_message=None
        )

        # Add rule to engine
        validation_service.add_business_rule(rule)

        return {
            "message": "Business rule created successfully",
            "rule_id": rule.id,
            "rule": make_json_serializable(rule.dict())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule creation failed: {str(e)}")


@router.get("/rules")
async def list_business_rules():
    """List all business rules."""
    try:
        rules = list(validation_service.business_rule_engine.rules.values())

        # Group by category
        rules_by_category = {}
        for rule in rules:
            if rule.category not in rules_by_category:
                rules_by_category[rule.category] = []
            rules_by_category[rule.category].append({
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "active": rule.active
            })

        return {
            "rules_by_category": rules_by_category,
            "total_rules": len(rules),
            "active_rules": len([r for r in rules if r.active])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list rules: {str(e)}")


@router.get("/rules/{rule_id}")
async def get_business_rule(rule_id: str):
    """Get a specific business rule by ID."""
    try:
        rule = validation_service.get_business_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        return make_json_serializable(rule.dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rule: {str(e)}")


@router.delete("/rules/{rule_id}")
async def delete_business_rule(rule_id: str):
    """Delete a business rule."""
    try:
        success = validation_service.remove_business_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"message": "Rule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")


@router.get("/rules/categories/{category}")
async def get_rules_by_category(category: str):
    """Get all rules in a specific category."""
    try:
        rules = validation_service.get_rules_by_category(category)
        return {
            "category": category,
            "rules": [make_json_serializable(rule.dict()) for rule in rules],
            "count": len(rules)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rules by category: {str(e)}")


# Industry template endpoints
@router.get("/templates")
async def list_industry_templates():
    """List available industry rule templates."""
    try:
        templates = validation_service.get_available_industry_templates()
        return {
            "available_templates": templates,
            "count": len(templates)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.post("/templates/{industry}/apply")
async def apply_industry_template(industry: str):
    """Apply an industry-specific rule template."""
    try:
        success = validation_service.apply_industry_template(industry)
        if not success:
            raise HTTPException(status_code=404, detail="Industry template not found")

        return {
            "message": f"Industry template '{industry}' applied successfully",
            "template": industry
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply template: {str(e)}")


# Validation history and analytics endpoints
@router.get("/history")
async def get_validation_history(limit: Optional[int] = 10):
    """Get validation history."""
    try:
        history = validation_service.get_validation_history(limit)

        # Convert to summary format for API response
        history_summary = []
        for report in history:
            history_summary.append({
                "id": report.id,
                "dataset_name": report.dataset_name,
                "validation_timestamp": report.validation_timestamp,
                "overall_valid": report.overall_valid,
                "data_quality_score": report.data_quality_score,
                "total_issues": report.total_issues,
                "execution_time_ms": report.total_execution_time_ms
            })

        return {
            "history": history_summary,
            "count": len(history_summary)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/history/{report_id}")
async def get_validation_report(report_id: str):
    """Get a specific validation report by ID."""
    try:
        report = None
        for r in validation_service.validation_history:
            if r.id == report_id:
                report = r
                break

        if not report:
            raise HTTPException(status_code=404, detail="Validation report not found")

        return make_json_serializable(report.dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")


@router.get("/analytics")
async def get_validation_analytics():
    """Get validation analytics and trends."""
    try:
        analytics = validation_service.get_validation_analytics()
        return analytics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


# Profile-specific endpoints
@router.post("/profile-file")
async def profile_file(file: UploadFile = File(...)):
    """
    Profile an uploaded file for comprehensive data analysis.

    Args:
        file: Uploaded file (CSV or Excel)

    Returns:
        Data profiling results
    """
    try:
        # Read file data
        filename = file.filename or "unknown"
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Perform profiling only
        validation_request = ValidationRequest(
            data=data,
            validation_types=["profile"],
            schema_id=None,
            rule_categories=None,
            context=None,
            options={"dataset_name": filename}
        )

        report = await validation_service.validate_comprehensive(validation_request)

        # Return just the profiling results
        if report.profiling_results:
            return make_json_serializable(report.profiling_results.dict())
        else:
            raise HTTPException(status_code=500, detail="Profiling failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profiling failed: {str(e)}")


@router.get("/info")
async def get_service_info():
    """Get comprehensive validation service information."""
    try:
        return validation_service.get_service_info()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service info: {str(e)}")
