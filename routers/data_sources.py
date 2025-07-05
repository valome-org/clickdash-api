"""
Data Sources Router - API endpoints for the new data source architecture
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import tempfile
import os
from pathlib import Path
from services.data_source_service import data_source_service
from dependencies.auth import get_current_active_user
from database.models import User
from utils.serialization import CustomJSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/data-sources/health")
async def health_check():
    """Health check for the data source service"""
    try:
        health_info = await data_source_service.health_check()
        return CustomJSONResponse(content=health_info)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-sources/supported-formats")
async def get_supported_formats():
    """Get all supported file formats"""
    try:
        formats = data_source_service.get_supported_formats()
        return CustomJSONResponse(content={
            "supported_formats": formats,
            "total_formats": len(formats)
        })
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-sources/registry")
async def get_registry_info():
    """Get information about the data source registry"""
    try:
        registry_info = data_source_service.get_registry_info()
        return CustomJSONResponse(content=registry_info)
    except Exception as e:
        logger.error(f"Error getting registry info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-sources/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze an uploaded file using the new data source architecture"""
    try:
        # Create temporary file
        filename = file.filename or "uploaded_file"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Analyze file using new architecture
            analysis_results = await data_source_service.analyze_file(tmp_file_path)

            if not analysis_results:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to analyze file. Please check the file format and try again."
                )

            return CustomJSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "analysis": analysis_results,
                "user": current_user.username
            })

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/data-sources/preview")
async def preview_file(
    file: UploadFile = File(...),
    limit: Optional[int] = Form(10),
    current_user: User = Depends(get_current_active_user)
):
    """Preview data from an uploaded file"""
    try:
        # Validate limit
        if limit is None or limit < 1:
            limit = 10
        elif limit > 100:
            limit = 100

        # Create temporary file
        filename = file.filename or "uploaded_file"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Get data using new architecture
            data = await data_source_service.get_data_from_file(tmp_file_path, limit=limit)

            if data is None:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to read file. Please check the file format and try again."
                )

            # Convert to JSON-serializable format
            preview_data = {
                "columns": list(data.columns),
                "data": data.head(limit).to_dict('records'),
                "total_rows": len(data),
                "preview_rows": len(data.head(limit)),
                "dtypes": {col: str(dtype) for col, dtype in data.dtypes.items()}
            }

            return CustomJSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "preview": preview_data,
                "user": current_user.username
            })

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/data-sources/validate")
async def validate_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Validate an uploaded file using the new data source architecture"""
    try:
        # Create temporary file
        filename = file.filename or "uploaded_file"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Create data source and validate
            data_source = await data_source_service.create_data_source_from_file(tmp_file_path)

            if not data_source:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to create data source from file"
                )

            validation_results = await data_source.validate_data()

            # Clean up data source
            await data_source.disconnect()

            return CustomJSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "validation": validation_results,
                "user": current_user.username
            })

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/data-sources/enhanced-upload")
async def enhanced_upload(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    chart_types: Optional[str] = Form(None),
    number_of_charts: Optional[int] = Form(3),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Enhanced upload endpoint that uses the new data source architecture"""
    try:
        # Create temporary file
        filename = file.filename or "uploaded_file"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Step 1: Analyze file with new architecture
            analysis_results = await data_source_service.analyze_file(tmp_file_path)

            if not analysis_results:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to analyze file with new architecture"
                )

            # Step 2: Get data for dashboard generation
            data = await data_source_service.get_data_from_file(tmp_file_path)

            if data is None:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to read data from file"
                )

            # Step 3: Prepare generation options
            generation_options = {
                "category": category,
                "chart_types": chart_types.split(",") if chart_types else [],
                "number_of_charts": number_of_charts or 3,
                "description": description
            }

            # Step 4: Generate dashboard (using existing dashboard service)
            from services.dashboard_service import DashboardService
            dashboard_service = DashboardService()

            # Convert new analysis format to legacy format for compatibility
            legacy_analysis = {
                "columns": analysis_results["metadata"]["data_schema"]["columns"],
                "rows": analysis_results["metadata"]["row_count"],
                "numeric_columns": analysis_results["metadata"]["data_schema"]["numeric_columns"],
                "categorical_columns": analysis_results["metadata"]["data_schema"]["categorical_columns"],
                "data_types": analysis_results["metadata"]["data_types"],
                "missing_values": {},  # Would need to be extracted from validation results
                "summary": {}  # Would need to be calculated
            }

            dashboard_config = await dashboard_service.generate_llm_dashboard(
                data, legacy_analysis, file.filename or "Unknown", generation_options
            )

            return CustomJSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "analysis": analysis_results,
                "dashboard_config": dashboard_config.dict(),
                "user": current_user.username,
                "enhanced_features": {
                    "data_quality_score": analysis_results["metadata"]["quality_score"],
                    "source_type": analysis_results["source_type"],
                    "validation_status": analysis_results["validation"]["status"],
                    "capabilities": analysis_results["capabilities"]
                }
            })

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enhanced upload failed: {str(e)}")


@router.get("/data-sources/demo")
async def demo_data_source_architecture():
    """Demo endpoint showing the new data source architecture capabilities"""
    try:
        registry_info = data_source_service.get_registry_info()
        supported_formats = data_source_service.get_supported_formats()

        return CustomJSONResponse(content={
            "message": "AI Dashboard Platform - New Data Source Architecture",
            "version": "1.0.0",
            "features": {
                "universal_data_source_interface": True,
                "automatic_format_detection": True,
                "data_quality_assessment": True,
                "metadata_extraction": True,
                "validation_pipeline": True,
                "streaming_support": True,
                "extensible_architecture": True
            },
            "supported_formats": supported_formats,
            "registered_sources": registry_info["registered_sources"],
            "capabilities": {
                "excel": {
                    "multiple_sheets": True,
                    "format_detection": True,
                    "data_validation": True,
                    "quality_scoring": True
                },
                "csv": {
                    "encoding_detection": True,
                    "delimiter_detection": True,
                    "data_validation": True,
                    "quality_scoring": True
                }
            },
            "next_steps": [
                "Add API data source adapter",
                "Add database connection adapter",
                "Implement data transformation pipeline",
                "Add AI-powered data cleaning",
                "Implement user validation workflow"
            ]
        })

    except Exception as e:
        logger.error(f"Error in demo endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
