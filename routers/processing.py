"""
Data Processing Router - API endpoints for Phase 2 universal data processing pipeline
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, Dict, Any
import tempfile
import os
from pathlib import Path
from services.processing_service import data_processing_service, ProcessingWorkflow, WORKFLOW_TEMPLATES
from dependencies.auth import get_current_active_user
from database.models import User
from utils.serialization import CustomJSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/processing/health")
async def health_check():
    """Health check for the data processing service"""
    try:
        metrics = await data_processing_service.get_processing_metrics()
        return CustomJSONResponse(content={
            "status": "healthy",
            "service": "data_processing_service",
            "metrics": metrics,
            "available_workflows": list(WORKFLOW_TEMPLATES.keys())
        })
    except Exception as e:
        logger.error(f"Processing health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processing/workflows")
async def get_available_workflows():
    """Get all available processing workflows with descriptions"""
    try:
        return CustomJSONResponse(content={
            "workflows": WORKFLOW_TEMPLATES,
            "total_workflows": len(WORKFLOW_TEMPLATES),
            "default_workflow": ProcessingWorkflow.COMPREHENSIVE_ANALYSIS
        })
    except Exception as e:
        logger.error(f"Error getting workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processing/process-file")
async def process_file(
    file: UploadFile = File(...),
    workflow: Optional[str] = Form(ProcessingWorkflow.COMPREHENSIVE_ANALYSIS),
    current_user: User = Depends(get_current_active_user)
):
    """Process an uploaded file using specified workflow"""
    try:
        if workflow not in WORKFLOW_TEMPLATES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow. Available workflows: {list(WORKFLOW_TEMPLATES.keys())}"
            )

        # Create temporary file
        filename = file.filename or "uploaded_file"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Process file using the processing service
            result = await data_processing_service.process_file(
                file_path=tmp_file_path,
                workflow=workflow
            )

            # Convert result to response format
            response_data = result.to_dict()
            response_data.update({
                "status": "success",
                "filename": file.filename,
                "workflow_used": workflow,
                "workflow_info": WORKFLOW_TEMPLATES[workflow],
                "user": current_user.username
            })

            return CustomJSONResponse(content=response_data)

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/processing/analyze-quality")
async def analyze_data_quality(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze data quality using quality-focused workflow"""
    try:
        # Create temporary file
        filename = file.filename or "uploaded_file"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Process with quality-focused workflow
            result = await data_processing_service.process_file(
                file_path=tmp_file_path,
                workflow=ProcessingWorkflow.QUALITY_FOCUSED
            )

            # Extract quality report
            quality_report = result.quality_report.dict() if result.quality_report else None

            return CustomJSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "processing_id": result.processing_id,
                "quality_report": quality_report,
                "overall_quality_score": quality_report["overall_quality_score"] if quality_report else 0,
                "user": current_user.username
            })

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except Exception as e:
        logger.error(f"Quality analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quality analysis failed: {str(e)}")


@router.get("/processing/demo")
async def demo_processing_pipeline():
    """Demo endpoint showcasing Phase 2 data processing capabilities"""
    try:
        metrics = await data_processing_service.get_processing_metrics()

        return CustomJSONResponse(content={
            "message": "AI Dashboard Platform - Phase 2: Universal Data Processing Pipeline",
            "version": "2.0.0",
            "phase_2_features": {
                "data_ingestion_layer": "Unified data intake from any source",
                "data_normalization_engine": "Convert all data to common internal format",
                "data_quality_assessment": "Comprehensive data quality evaluation"
            },
            "available_workflows": WORKFLOW_TEMPLATES,
            "processing_metrics": metrics,
            "next_phase": "Phase 3: Advanced Data Validation System"
        })

    except Exception as e:
        logger.error(f"Error in demo endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
