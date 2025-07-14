"""
Metadata management API router.

This router provides comprehensive metadata management endpoints including:
- Automatic metadata extraction
- User metadata enhancement
- Metadata validation and quality scoring
- Metadata search and discovery
- Metadata lineage tracking
- Template and custom field management
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import io
import json
from datetime import datetime

from services.metadata_service import (
    MetadataService,
    MetadataSearchRequest,
    MetadataSearchResult,
    MetadataLineageRequest,
    MetadataSummaryRequest,
    MetadataSummary
)
from core.metadata import (
    MetadataEnhancementRequest,
    MetadataEnhancementResult,
    MetadataValidationResult,
    MetadataExtractionResult,
    DatasetMetadata,
    UserEnhancedMetadata,
    MetadataTemplate,
    CustomMetadataField,
    MetadataType,
    MetadataStatus,
    BusinessMeaning,
    SensitivityMarking,
    DataPrivacyLevel
)
from utils.serialization import make_json_serializable
from dependencies.auth import get_current_user

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

# Initialize metadata service
metadata_service = MetadataService()


@router.post("/extract", response_model=Dict[str, Any])
async def extract_metadata(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user = Depends(get_current_user)
):
    """
    Extract metadata automatically from uploaded data file.

    Args:
        file: Data file to extract metadata from
        name: Optional dataset name
        description: Optional dataset description
        current_user: Current authenticated user

    Returns:
        Extracted metadata information
    """
    try:
        # Read file based on type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        if file.filename.endswith('.csv'):
            content = await file.read()
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

        # Set context
        metadata_service.context.user_id = current_user.user_id

        # Extract metadata
        extraction_options = {
            'name': name or file.filename,
            'description': description,
            'source_id': file.filename,
            'user_id': current_user.user_id
        }

        result = await metadata_service.extract_metadata(df, **extraction_options)

        if result.success:
            return {
                "success": True,
                "dataset_metadata": make_json_serializable(result.dataset_metadata.dict()) if result.dataset_metadata else None,
                "performance_metrics": result.performance_metrics,
                "recommendations": result.recommendations
            }
        else:
            return {
                "success": False,
                "errors": result.errors,
                "warnings": result.warnings
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata extraction failed: {str(e)}")


@router.post("/enhance", response_model=Dict[str, Any])
async def enhance_metadata(
    request: MetadataEnhancementRequest,
    current_user = Depends(get_current_user)
):
    """
    Enhance metadata with user-provided information.

    Args:
        request: Enhancement request with user data
        current_user: Current authenticated user

    Returns:
        Enhanced metadata information
    """
    try:
        # Set user context
        request.user_id = current_user.user_id
        metadata_service.context.user_id = current_user.user_id

        # Enhance metadata
        result = await metadata_service.enhance_metadata(request)

        if result.success:
            return {
                "success": True,
                "element_id": result.element_id,
                "enhanced_metadata": make_json_serializable(result.enhanced_metadata.dict()) if result.enhanced_metadata else None,
                "validation_results": result.validation_results,
                "suggestions": result.suggestions
            }
        else:
            return {
                "success": False,
                "element_id": result.element_id,
                "validation_results": result.validation_results,
                "warnings": result.warnings
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata enhancement failed: {str(e)}")


@router.get("/validate/{element_id}", response_model=Dict[str, Any])
async def validate_metadata(
    element_id: str,
    current_user = Depends(get_current_user)
):
    """
    Validate metadata for quality and consistency.

    Args:
        element_id: ID of element to validate
        current_user: Current authenticated user

    Returns:
        Validation results and quality scores
    """
    try:
        # Set user context
        metadata_service.context.user_id = current_user.user_id

        # Validate metadata
        result = await metadata_service.validate_metadata(element_id)

        return {
            "element_id": result.element_id,
            "element_type": result.element_type,
            "overall_score": result.overall_score,
            "scores": {
                "completeness": result.completeness_score,
                "consistency": result.consistency_score,
                "accuracy": result.accuracy_score,
                "business_value": result.business_value_score
            },
            "issues": [make_json_serializable(issue.dict()) for issue in result.issues],
            "issue_counts": {
                "critical": result.critical_count,
                "error": result.error_count,
                "warning": result.warning_count,
                "info": result.info_count
            },
            "recommendations": result.recommendations,
            "auto_fix_suggestions": result.auto_fix_suggestions,
            "validated_at": result.validated_at.isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata validation failed: {str(e)}")


@router.post("/validate/batch", response_model=List[Dict[str, Any]])
async def batch_validate_metadata(
    element_ids: List[str],
    current_user = Depends(get_current_user)
):
    """
    Validate multiple metadata elements.

    Args:
        element_ids: List of element IDs to validate
        current_user: Current authenticated user

    Returns:
        List of validation results
    """
    try:
        # Set user context
        metadata_service.context.user_id = current_user.user_id

        # Batch validate
        results = await metadata_service.batch_validate_metadata(element_ids)

        return [
            {
                "element_id": result.element_id,
                "element_type": result.element_type,
                "overall_score": result.overall_score,
                "issue_counts": {
                    "critical": result.critical_count,
                    "error": result.error_count,
                    "warning": result.warning_count,
                    "info": result.info_count
                },
                "recommendations": result.recommendations[:3]  # Limit for batch response
            }
            for result in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch validation failed: {str(e)}")


@router.post("/search", response_model=Dict[str, Any])
async def search_metadata(
    request: MetadataSearchRequest,
    current_user = Depends(get_current_user)
):
    """
    Search metadata based on query and filters.

    Args:
        request: Search request with query and filters
        current_user: Current authenticated user

    Returns:
        Search results with facets
    """
    try:
        # Set user context
        metadata_service.context.user_id = current_user.user_id

        # Search metadata
        result = await metadata_service.search_metadata(request)

        # Serialize results
        serialized_results = []
        for metadata in result.results:
            serialized_results.append(make_json_serializable(metadata.dict()))

        return {
            "total_count": result.total_count,
            "results": serialized_results,
            "facets": result.facets,
            "query_time_ms": result.query_time_ms,
            "pagination": {
                "limit": request.limit,
                "offset": request.offset,
                "has_more": result.total_count > (request.offset + request.limit)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata search failed: {str(e)}")


@router.get("/lineage/{element_id}", response_model=Dict[str, Any])
async def get_metadata_lineage(
    element_id: str,
    direction: str = "both",
    depth: int = 3,
    include_technical: bool = True,
    include_business: bool = True,
    current_user = Depends(get_current_user)
):
    """
    Get lineage information for a metadata element.

    Args:
        element_id: Element ID to trace lineage for
        direction: Lineage direction (upstream, downstream, both)
        depth: Maximum lineage depth
        include_technical: Include technical lineage
        include_business: Include business lineage
        current_user: Current authenticated user

    Returns:
        Lineage graph information
    """
    try:
        # Set user context
        metadata_service.context.user_id = current_user.user_id

        # Create lineage request
        lineage_request = MetadataLineageRequest(
            element_id=element_id,
            direction=direction,
            depth=depth,
            include_technical=include_technical,
            include_business=include_business
        )

        # Get lineage
        lineage = await metadata_service.get_metadata_lineage(lineage_request)

        return lineage

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lineage retrieval failed: {str(e)}")


@router.get("/summary", response_model=Dict[str, Any])
async def get_metadata_summary(
    scope: str = "all",
    filters: Optional[str] = None,
    group_by: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get summary statistics for metadata.

    Args:
        scope: Summary scope (all, dataset, column)
        filters: JSON string of filters to apply
        group_by: Comma-separated grouping dimensions
        current_user: Current authenticated user

    Returns:
        Metadata summary statistics
    """
    try:
        # Set user context
        metadata_service.context.user_id = current_user.user_id

        # Parse filters
        parsed_filters = None
        if filters:
            try:
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filters JSON")

        # Parse group_by
        parsed_group_by = None
        if group_by:
            parsed_group_by = [g.strip() for g in group_by.split(",")]

        # Create summary request
        summary_request = MetadataSummaryRequest(
            scope=scope,
            filters=parsed_filters,
            group_by=parsed_group_by
        )

        # Get summary
        summary = await metadata_service.get_metadata_summary(summary_request)

        return make_json_serializable(summary.dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


@router.get("/{element_id}", response_model=Dict[str, Any])
async def get_metadata(
    element_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get metadata for a specific element.

    Args:
        element_id: Element ID to retrieve
        current_user: Current authenticated user

    Returns:
        Metadata information
    """
    try:
        # Get metadata
        metadata = await metadata_service.get_metadata(element_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Metadata not found for element {element_id}")

        return {
            "element_id": element_id,
            "metadata": make_json_serializable(metadata.dict())
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata retrieval failed: {str(e)}")


@router.get("/", response_model=Dict[str, Any])
async def list_metadata(
    metadata_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_user)
):
    """
    List metadata with optional filtering.

    Args:
        metadata_type: Filter by metadata type
        limit: Maximum results to return
        offset: Result offset for pagination
        current_user: Current authenticated user

    Returns:
        List of metadata elements
    """
    try:
        # Parse metadata type
        parsed_type = None
        if metadata_type:
            try:
                parsed_type = MetadataType(metadata_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid metadata type: {metadata_type}")

        # List metadata
        metadata_list = await metadata_service.list_metadata(
            metadata_type=parsed_type,
            limit=limit,
            offset=offset
        )

        # Serialize results
        serialized_list = []
        for metadata in metadata_list:
            serialized_list.append(make_json_serializable(metadata.dict()))

        return {
            "metadata": serialized_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(serialized_list)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata listing failed: {str(e)}")


@router.delete("/{element_id}", response_model=Dict[str, Any])
async def delete_metadata(
    element_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete metadata for an element.

    Args:
        element_id: Element ID to delete
        current_user: Current authenticated user

    Returns:
        Deletion confirmation
    """
    try:
        # Delete metadata
        success = await metadata_service.delete_metadata(element_id)

        if success:
            return {
                "success": True,
                "message": f"Metadata deleted for element {element_id}",
                "element_id": element_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Metadata not found for element {element_id}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata deletion failed: {str(e)}")


# Template Management Endpoints

@router.post("/templates", response_model=Dict[str, Any])
async def create_metadata_template(
    template: MetadataTemplate,
    current_user = Depends(get_current_user)
):
    """
    Create a new metadata enhancement template.

    Args:
        template: Template definition
        current_user: Current authenticated user

    Returns:
        Created template information
    """
    try:
        # Set creator
        template.created_by = current_user.user_id

        # Create template
        template_id = await metadata_service.create_template(template)

        return {
            "success": True,
            "template_id": template_id,
            "template": make_json_serializable(template.dict())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template creation failed: {str(e)}")


@router.post("/custom-fields", response_model=Dict[str, Any])
async def add_custom_metadata_field(
    field: CustomMetadataField,
    current_user = Depends(get_current_user)
):
    """
    Add a custom metadata field definition.

    Args:
        field: Custom field definition
        current_user: Current authenticated user

    Returns:
        Created field information
    """
    try:
        # Set creator
        field.created_by = current_user.user_id

        # Add custom field
        field_id = await metadata_service.add_custom_field(field)

        return {
            "success": True,
            "field_id": field_id,
            "field": make_json_serializable(field.dict())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom field creation failed: {str(e)}")


# Quick Enhancement Endpoints

@router.post("/quick-enhance/{element_id}", response_model=Dict[str, Any])
async def quick_enhance_metadata(
    element_id: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    business_meaning: Optional[str] = None,
    privacy_level: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Quick enhancement of metadata with common fields.

    Args:
        element_id: Element to enhance
        display_name: User-friendly display name
        description: Element description
        tags: List of tags
        business_meaning: Business meaning description
        privacy_level: Privacy classification level
        current_user: Current authenticated user

    Returns:
        Enhanced metadata information
    """
    try:
        # Build enhancement data
        enhancements = {}

        if display_name:
            enhancements["display_name"] = display_name

        if description:
            enhancements["description"] = description

        if tags:
            enhancements["tags"] = tags

        if business_meaning:
            enhancements["business_meaning"] = {
                "primary_meaning": business_meaning
            }

        if privacy_level:
            try:
                privacy_enum = DataPrivacyLevel(privacy_level)
                enhancements["sensitivity_marking"] = {
                    "privacy_level": privacy_enum
                }
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid privacy level: {privacy_level}")

        # Create enhancement request
        request = MetadataEnhancementRequest(
            element_id=element_id,
            element_type=MetadataType.COLUMN,  # Default, will be updated based on element
            enhancements=enhancements,
            user_id=current_user.user_id,
            notes="Quick enhancement via API"
        )

        # Enhance metadata
        result = await metadata_service.enhance_metadata(request)

        if result.success:
            return {
                "success": True,
                "element_id": result.element_id,
                "enhanced_fields": list(enhancements.keys()),
                "validation_results": result.validation_results
            }
        else:
            return {
                "success": False,
                "element_id": result.element_id,
                "validation_results": result.validation_results,
                "warnings": result.warnings
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick enhancement failed: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def metadata_health_check():
    """
    Health check for metadata service.

    Returns:
        Service health information
    """
    return {
        "status": "healthy",
        "service": "metadata_management",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": [
            "automatic_extraction",
            "user_enhancement",
            "validation",
            "search",
            "lineage_tracking"
        ]
    }
