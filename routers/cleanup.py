"""
FastAPI router for data cleanup endpoints.

This module provides REST API endpoints for all cleanup functionality including:
- Comprehensive data cleanup
- Outlier detection and handling
- Duplicate resolution
- Missing data imputation
- Data transformation recommendations
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import pandas as pd
import io
import logging

from services.cleanup_service import cleanup_service, CleanupRequest, CleanupReport
from core.cleanup import (
    CleanupStrategy,
    OutlierDetectionMethod,
    OutlierHandlingStrategy,
    DuplicateDetectionType,
    DuplicateResolutionStrategy,
    ImputationMethod,
    ImputationStrategy,
    TransformationType
)
from utils.serialization import make_json_serializable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cleanup", tags=["cleanup"])


# Comprehensive Cleanup Endpoints

@router.post("/cleanup-file", response_class=JSONResponse)
async def cleanup_file(
    file: UploadFile = File(...),
    cleanup_types: List[str] = Query(default=["outliers", "duplicates", "missing", "transformations"]),
    strategy: CleanupStrategy = Query(default=CleanupStrategy.SUGGEST),
    aggressiveness: float = Query(default=0.5, ge=0.0, le=1.0),
    preserve_original: bool = Query(default=True)
):
    """
    Upload and clean a data file using comprehensive cleanup operations.

    Supports CSV and Excel files.
    """
    try:
        filename = file.filename or "unknown"

        # Load data based on file type
        try:
            if filename.endswith('.csv'):
                content = await file.read()
                data = pd.read_csv(io.StringIO(content.decode('utf-8')))
            elif filename.endswith(('.xlsx', '.xls')):
                content = await file.read()
                data = pd.read_excel(io.BytesIO(content))
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format. Please use CSV or Excel files.")

            # Ensure data is a valid DataFrame
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Failed to load data as DataFrame")

            # Check if DataFrame is empty
            if len(data) == 0:
                raise ValueError("Uploaded file contains no data")

        except Exception as e:
            logger.error(f"Failed to load file data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to load file: {str(e)}")

        # Create cleanup request
        cleanup_request = CleanupRequest(
            data=data,
            cleanup_types=cleanup_types,
            strategy=strategy,
            aggressiveness=aggressiveness,
            preserve_original=preserve_original,
            outlier_method=None,
            outlier_strategy=None,
            duplicate_detection=None,
            duplicate_strategy=None,
            imputation_method=None,
            imputation_strategy=None,
            target_columns=None,
            context=None,
            options={"dataset_name": filename}
        )

        # Perform cleanup
        result = await cleanup_service.cleanup_comprehensive(cleanup_request)

        # Convert to JSON-serializable format
        return make_json_serializable(result.dict())

    except Exception as e:
        logger.error(f"File cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/cleanup-data", response_class=JSONResponse)
async def cleanup_data(
    request: CleanupRequest
):
    """
    Clean provided data using comprehensive cleanup operations.
    """
    try:
        result = await cleanup_service.cleanup_comprehensive(request)
        return make_json_serializable(result.dict())

    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# Outlier Handling Endpoints

@router.post("/outliers/detect-file", response_class=JSONResponse)
async def detect_outliers_file(
    file: UploadFile = File(...),
    method: OutlierDetectionMethod = Query(default=OutlierDetectionMethod.IQR),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Detect outliers in uploaded file data.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Detect outliers
        issues = await cleanup_service.outlier_handler.analyze_data(data)

        return make_json_serializable({
            "filename": filename,
            "outliers_detected": len(issues),
            "issues": [issue.dict() for issue in issues]
        })

    except Exception as e:
        logger.error(f"Outlier detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Outlier detection failed: {str(e)}")


@router.post("/outliers/handle-file", response_class=JSONResponse)
async def handle_outliers_file(
    file: UploadFile = File(...),
    method: OutlierDetectionMethod = Query(default=OutlierDetectionMethod.IQR),
    strategy: OutlierHandlingStrategy = Query(default=OutlierHandlingStrategy.CAP),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Handle outliers in uploaded file data.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Handle outliers
        kwargs = {'method': method, 'strategy': strategy, 'columns': columns}
        result = await cleanup_service.outlier_handler.clean(data, None, **kwargs)

        return make_json_serializable(result.dict())

    except Exception as e:
        logger.error(f"Outlier handling failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Outlier handling failed: {str(e)}")


# Duplicate Resolution Endpoints

@router.post("/duplicates/detect-file", response_class=JSONResponse)
async def detect_duplicates_file(
    file: UploadFile = File(...),
    detection_type: DuplicateDetectionType = Query(default=DuplicateDetectionType.EXACT),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Detect duplicates in uploaded file data.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Detect duplicates
        issues = await cleanup_service.duplicate_resolver.analyze_data(data)

        return make_json_serializable({
            "filename": filename,
            "duplicate_groups_detected": len(issues),
            "issues": [issue.dict() for issue in issues]
        })

    except Exception as e:
        logger.error(f"Duplicate detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Duplicate detection failed: {str(e)}")


@router.post("/duplicates/resolve-file", response_class=JSONResponse)
async def resolve_duplicates_file(
    file: UploadFile = File(...),
    detection_type: DuplicateDetectionType = Query(default=DuplicateDetectionType.EXACT),
    strategy: DuplicateResolutionStrategy = Query(default=DuplicateResolutionStrategy.KEEP_FIRST),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Resolve duplicates in uploaded file data.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Resolve duplicates
        kwargs = {'detection_type': detection_type, 'strategy': strategy, 'columns': columns}
        result = await cleanup_service.duplicate_resolver.clean(data, None, **kwargs)

        return make_json_serializable(result.dict())

    except Exception as e:
        logger.error(f"Duplicate resolution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Duplicate resolution failed: {str(e)}")


# Missing Data Imputation Endpoints

@router.post("/imputation/analyze-file", response_class=JSONResponse)
async def analyze_missing_data_file(
    file: UploadFile = File(...),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Analyze missing data patterns in uploaded file.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Analyze missing data
        issues = await cleanup_service.imputation_engine.analyze_data(data)

        # Calculate missing data statistics
        missing_stats = {
            "total_missing_values": data.isnull().sum().sum(),
            "columns_with_missing": data.isnull().any().sum(),
            "missing_percentage": (data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100
        }

        return make_json_serializable({
            "filename": filename,
            "missing_data_statistics": missing_stats,
            "issues": [issue.dict() for issue in issues]
        })

    except Exception as e:
        logger.error(f"Missing data analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Missing data analysis failed: {str(e)}")


@router.post("/imputation/impute-file", response_class=JSONResponse)
async def impute_missing_data_file(
    file: UploadFile = File(...),
    method: ImputationMethod = Query(default=ImputationMethod.MEDIAN),
    strategy: ImputationStrategy = Query(default=ImputationStrategy.AUTOMATIC),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Impute missing data in uploaded file.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Impute missing data
        kwargs = {'method': method, 'strategy': strategy, 'columns': columns}
        result = await cleanup_service.imputation_engine.clean(data, None, **kwargs)

        return make_json_serializable(result.dict())

    except Exception as e:
        logger.error(f"Missing data imputation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Missing data imputation failed: {str(e)}")


# Data Transformation Endpoints

@router.post("/transformations/analyze-file", response_class=JSONResponse)
async def analyze_transformations_file(
    file: UploadFile = File(...),
    transformation_types: Optional[List[TransformationType]] = Query(default=None)
):
    """
    Analyze transformation opportunities in uploaded file.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Analyze transformations
        issues = await cleanup_service.transformation_recommender.analyze_data(data)

        # Group suggestions by type
        suggestion_summary = {}
        for issue in issues:
            trans_type = issue.metadata.get('transformation_type', 'unknown')
            suggestion_summary[trans_type] = suggestion_summary.get(trans_type, 0) + 1

        return make_json_serializable({
            "filename": filename,
            "total_suggestions": len(issues),
            "suggestions_by_type": suggestion_summary,
            "issues": [issue.dict() for issue in issues]
        })

    except Exception as e:
        logger.error(f"Transformation analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transformation analysis failed: {str(e)}")


@router.post("/transformations/apply-file", response_class=JSONResponse)
async def apply_transformations_file(
    file: UploadFile = File(...),
    apply_transformations: bool = Query(default=True),
    transformation_types: Optional[List[str]] = Query(default=None)
):
    """
    Apply transformation recommendations to uploaded file.
    """
    try:
        filename = file.filename or "unknown"

        # Load data
        if filename.endswith('.csv'):
            content = await file.read()
            data = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            content = await file.read()
            data = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Apply transformations
        kwargs = {
            'apply_transformations': apply_transformations,
            'transformation_types': transformation_types
        }
        result = await cleanup_service.transformation_recommender.clean(data, None, **kwargs)

        return make_json_serializable(result.dict())

    except Exception as e:
        logger.error(f"Transformation application failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transformation application failed: {str(e)}")


# Service Information and Analytics Endpoints

@router.get("/service-info", response_class=JSONResponse)
async def get_cleanup_service_info():
    """
    Get information about the cleanup service and its components.
    """
    try:
        service_info = cleanup_service.get_service_info()
        return make_json_serializable(service_info)

    except Exception as e:
        logger.error(f"Failed to get service info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get service info: {str(e)}")


@router.get("/analytics", response_class=JSONResponse)
async def get_cleanup_analytics():
    """
    Get analytics and statistics from cleanup operations.
    """
    try:
        analytics = cleanup_service.get_cleanup_analytics()
        return make_json_serializable(analytics)

    except Exception as e:
        logger.error(f"Failed to get cleanup analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cleanup analytics: {str(e)}")


@router.get("/history", response_class=JSONResponse)
async def get_cleanup_history(
    limit: Optional[int] = Query(default=10, ge=1, le=100)
):
    """
    Get cleanup operation history.
    """
    try:
        history = cleanup_service.get_cleanup_history(limit)
        return make_json_serializable([report.dict() for report in history])

    except Exception as e:
        logger.error(f"Failed to get cleanup history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cleanup history: {str(e)}")


# Method and Strategy Information Endpoints

@router.get("/methods/outliers", response_class=JSONResponse)
async def get_outlier_methods():
    """Get available outlier detection methods and handling strategies."""
    return {
        "detection_methods": [method.value for method in OutlierDetectionMethod],
        "handling_strategies": [strategy.value for strategy in OutlierHandlingStrategy]
    }


@router.get("/methods/duplicates", response_class=JSONResponse)
async def get_duplicate_methods():
    """Get available duplicate detection types and resolution strategies."""
    return {
        "detection_types": [dtype.value for dtype in DuplicateDetectionType],
        "resolution_strategies": [strategy.value for strategy in DuplicateResolutionStrategy]
    }


@router.get("/methods/imputation", response_class=JSONResponse)
async def get_imputation_methods():
    """Get available imputation methods and strategies."""
    return {
        "imputation_methods": [method.value for method in ImputationMethod],
        "imputation_strategies": [strategy.value for strategy in ImputationStrategy]
    }


@router.get("/methods/transformations", response_class=JSONResponse)
async def get_transformation_types():
    """Get available transformation types."""
    return {
        "transformation_types": [ttype.value for ttype in TransformationType]
    }


@router.get("/strategies", response_class=JSONResponse)
async def get_cleanup_strategies():
    """Get available cleanup strategies."""
    return {
        "cleanup_strategies": [strategy.value for strategy in CleanupStrategy]
    }
