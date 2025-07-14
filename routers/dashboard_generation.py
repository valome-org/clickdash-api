"""
Dashboard Generation API Router.

This router provides REST endpoints for Phase 8 dashboard generation including:
- Dynamic dashboard building and updates
- Export and integration capabilities
- Version control and rollback
- Update notifications and collaboration
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime

from database.models import User
from dependencies.auth import get_current_active_user
from services.dashboard_generation_service import dashboard_generation_service
from models.dashboard import DashboardConfig
from utils.serialization import CustomJSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class GenerateDashboardRequest(BaseModel):
    """Request to generate dashboard from workflow."""
    workflow_id: str
    dashboard_config: DashboardConfig
    data: Dict[str, Any]
    generation_options: Optional[Dict[str, Any]] = None


class UpdateDashboardRequest(BaseModel):
    """Request to update existing dashboard."""
    updated_config: DashboardConfig
    change_summary: str
    data: Optional[Dict[str, Any]] = None


class RollbackDashboardRequest(BaseModel):
    """Request to rollback dashboard."""
    target_version_id: str
    rollback_reason: str


class ExportDashboardRequest(BaseModel):
    """Request to export dashboard."""
    export_format: str
    quality: str = "medium"
    include_data: bool = True
    include_interactivity: bool = True
    custom_branding: Dict[str, Any] = Field(default_factory=dict)
    integration_platform: Optional[str] = None
    integration_config: Dict[str, Any] = Field(default_factory=dict)


class CreateIntegrationRequest(BaseModel):
    """Request to create integration."""
    platform: str
    integration_config: Dict[str, Any]


class EmbedCodeRequest(BaseModel):
    """Request to generate embed code."""
    platform: str = "website"
    width: str = "100%"
    height: str = "600px"
    theme: str = "light"
    interactive: bool = True
    show_controls: bool = True


class APIEndpointRequest(BaseModel):
    """Request to create API endpoints."""
    enable_filters: bool = True
    enable_realtime: bool = False


# Dashboard Generation Endpoints

@router.post("/dashboard/generate")
async def generate_dashboard_from_workflow(
    request: GenerateDashboardRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate dashboard from approved workflow."""
    try:
        logger.info(f"Generating dashboard from workflow {request.workflow_id}")

        result = await dashboard_generation_service.generate_dashboard_from_workflow(
            workflow_id=request.workflow_id,
            dashboard_config=request.dashboard_config,
            data=request.data,
            user=current_user,
            generation_options=request.generation_options
        )

        return CustomJSONResponse(content={
            "success": result.success,
            "dashboard_id": result.dashboard_id,
            "generation_strategy": result.generation_strategy.value,
            "generation_time_ms": result.generation_time_ms,
            "performance_score": result.performance_score,
            "accessibility_score": result.accessibility_score,
            "responsive_score": result.responsive_score,
            "layout_specification": result.layout_specification,
            "rendered_components": result.rendered_components,
            "warnings": result.warnings,
            "recommendations": result.recommendations
        })

    except Exception as e:
        logger.error(f"Dashboard generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard generation failed: {str(e)}"
        )


@router.get("/dashboard/{dashboard_id}/status")
async def get_generation_status(
    dashboard_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get generation status for a dashboard."""
    try:
        status_info = await dashboard_generation_service.get_generation_status(dashboard_id)

        return CustomJSONResponse(content=status_info)

    except Exception as e:
        logger.error(f"Failed to get generation status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get generation status: {str(e)}"
        )


# Dashboard Update Endpoints

@router.put("/dashboard/{dashboard_id}")
async def update_dashboard(
    dashboard_id: str,
    request: UpdateDashboardRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update existing dashboard with version control."""
    try:
        logger.info(f"Updating dashboard {dashboard_id}")

        result = await dashboard_generation_service.update_dashboard(
            dashboard_id=dashboard_id,
            updated_config=request.updated_config,
            user=current_user,
            change_summary=request.change_summary,
            data=request.data
        )

        return CustomJSONResponse(content={
            "success": result.success,
            "dashboard_id": result.dashboard_id,
            "generation_time_ms": result.generation_time_ms,
            "performance_score": result.performance_score,
            "layout_specification": result.layout_specification,
            "warnings": result.warnings,
            "recommendations": result.recommendations
        })

    except Exception as e:
        logger.error(f"Dashboard update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard update failed: {str(e)}"
        )


@router.post("/dashboard/{dashboard_id}/rollback")
async def rollback_dashboard(
    dashboard_id: str,
    request: RollbackDashboardRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Rollback dashboard to a previous version."""
    try:
        logger.info(f"Rolling back dashboard {dashboard_id} to version {request.target_version_id}")

        result = await dashboard_generation_service.rollback_dashboard(
            dashboard_id=dashboard_id,
            target_version_id=request.target_version_id,
            user=current_user,
            rollback_reason=request.rollback_reason
        )

        return CustomJSONResponse(content={
            "success": result.success,
            "dashboard_id": result.dashboard_id,
            "message": f"Dashboard rolled back to version {request.target_version_id}",
            "generation_time_ms": result.generation_time_ms
        })

    except Exception as e:
        logger.error(f"Dashboard rollback failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard rollback failed: {str(e)}"
        )


# Version Control Endpoints

@router.get("/dashboard/{dashboard_id}/versions")
async def get_dashboard_versions(
    dashboard_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """Get version history for a dashboard."""
    try:
        versions = await dashboard_generation_service.get_dashboard_versions(
            dashboard_id, limit, offset
        )

        return CustomJSONResponse(content={
            "dashboard_id": dashboard_id,
            "versions": [
                {
                    "version_id": v.version_id,
                    "version_number": v.version_number,
                    "version_name": v.version_name,
                    "status": v.status.value,
                    "created_by": v.created_by,
                    "created_at": v.created_at.isoformat(),
                    "published_at": v.published_at.isoformat() if v.published_at else None,
                    "change_summary": v.change_summary,
                    "size_bytes": v.size_bytes,
                    "performance_score": v.performance_score,
                    "quality_score": v.quality_score
                }
                for v in versions
            ],
            "total": len(versions),
            "limit": limit,
            "offset": offset
        })

    except Exception as e:
        logger.error(f"Failed to get dashboard versions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard versions: {str(e)}"
        )


@router.get("/dashboard/{dashboard_id}/versions/compare")
async def compare_dashboard_versions(
    dashboard_id: str,
    version_1: str = Query(..., description="First version ID"),
    version_2: str = Query(..., description="Second version ID"),
    current_user: User = Depends(get_current_active_user)
):
    """Compare two versions of a dashboard."""
    try:
        comparison = await dashboard_generation_service.compare_dashboard_versions(
            dashboard_id, version_1, version_2
        )

        return CustomJSONResponse(content={
            "dashboard_id": dashboard_id,
            "version_1": version_1,
            "version_2": version_2,
            "comparison": comparison
        })

    except Exception as e:
        logger.error(f"Version comparison failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Version comparison failed: {str(e)}"
        )


# Export Endpoints

@router.post("/dashboard/{dashboard_id}/export")
async def export_dashboard(
    dashboard_id: str,
    request: ExportDashboardRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Export dashboard in specified format."""
    try:
        from core.dashboard.export_system import ExportFormat, IntegrationPlatform

        logger.info(f"Exporting dashboard {dashboard_id} as {request.export_format}")

        # Convert string to enum
        export_format = ExportFormat(request.export_format)

        export_options = {
            "quality": request.quality,
            "include_data": request.include_data,
            "include_interactivity": request.include_interactivity,
            "custom_branding": request.custom_branding
        }

        if request.integration_platform:
            export_options["integration_platform"] = IntegrationPlatform(request.integration_platform)
            export_options["integration_config"] = request.integration_config

        result = await dashboard_generation_service.export_dashboard(
            dashboard_id=dashboard_id,
            export_format=export_format,
            user=current_user,
            export_options=export_options
        )

        return CustomJSONResponse(content={
            "success": result.success,
            "export_id": result.export_id,
            "export_format": result.export_format.value,
            "file_path": result.file_path,
            "file_url": result.file_url,
            "file_size": result.file_size,
            "embed_code": result.embed_code,
            "api_endpoint": result.api_endpoint,
            "integration_link": result.integration_link,
            "generation_time_ms": result.generation_time_ms,
            "warnings": result.warnings,
            "errors": result.errors
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Dashboard export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard export failed: {str(e)}"
        )


@router.post("/dashboard/{dashboard_id}/embed")
async def generate_embed_code(
    dashboard_id: str,
    request: EmbedCodeRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate embed code for dashboard."""
    try:
        embed_options = {
            "width": request.width,
            "height": request.height,
            "theme": request.theme,
            "interactive": request.interactive,
            "show_controls": request.show_controls
        }

        embed_code = await dashboard_generation_service.generate_embed_code(
            dashboard_id=dashboard_id,
            platform=request.platform,
            embed_options=embed_options
        )

        return CustomJSONResponse(content={
            "dashboard_id": dashboard_id,
            "platform": request.platform,
            "embed_code": embed_code,
            "instructions": f"Copy and paste this code into your {request.platform}"
        })

    except Exception as e:
        logger.error(f"Embed code generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embed code generation failed: {str(e)}"
        )


@router.post("/dashboard/{dashboard_id}/api")
async def create_api_endpoints(
    dashboard_id: str,
    request: APIEndpointRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create API endpoints for dashboard data access."""
    try:
        api_options = {
            "enable_filters": request.enable_filters,
            "enable_realtime": request.enable_realtime
        }

        endpoints = await dashboard_generation_service.create_api_endpoints(
            dashboard_id=dashboard_id,
            api_options=api_options
        )

        return CustomJSONResponse(content={
            "dashboard_id": dashboard_id,
            "endpoints": endpoints,
            "authentication": "Bearer token required in Authorization header",
            "documentation": f"https://api.clickdash.com/docs/dashboards/{dashboard_id}"
        })

    except Exception as e:
        logger.error(f"API endpoint creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API endpoint creation failed: {str(e)}"
        )


# Integration Endpoints

@router.post("/dashboard/{dashboard_id}/integration")
async def create_integration(
    dashboard_id: str,
    request: CreateIntegrationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create integration with external platform."""
    try:
        from core.dashboard.export_system import IntegrationPlatform

        platform = IntegrationPlatform(request.platform)

        integration_result = await dashboard_generation_service.create_integration(
            dashboard_id=dashboard_id,
            platform=platform,
            user=current_user,
            integration_config=request.integration_config
        )

        return CustomJSONResponse(content={
            "dashboard_id": dashboard_id,
            "integration": integration_result
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration platform: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Integration creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integration creation failed: {str(e)}"
        )


# Notification Endpoints

@router.post("/dashboard/{dashboard_id}/subscribe")
async def subscribe_to_updates(
    dashboard_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Subscribe to dashboard update notifications."""
    try:
        success = await dashboard_generation_service.subscribe_to_dashboard_updates(
            dashboard_id, current_user
        )

        return CustomJSONResponse(content={
            "success": success,
            "message": f"Subscribed to updates for dashboard {dashboard_id}"
        })

    except Exception as e:
        logger.error(f"Subscription failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subscription failed: {str(e)}"
        )


@router.delete("/dashboard/{dashboard_id}/subscribe")
async def unsubscribe_from_updates(
    dashboard_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Unsubscribe from dashboard update notifications."""
    try:
        success = await dashboard_generation_service.unsubscribe_from_dashboard_updates(
            dashboard_id, current_user
        )

        return CustomJSONResponse(content={
            "success": success,
            "message": f"Unsubscribed from updates for dashboard {dashboard_id}"
        })

    except Exception as e:
        logger.error(f"Unsubscription failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsubscription failed: {str(e)}"
        )


@router.get("/notifications")
async def get_user_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """Get notifications for the current user."""
    try:
        notifications = await dashboard_generation_service.get_user_notifications(
            current_user, limit, unread_only
        )

        return CustomJSONResponse(content={
            "notifications": notifications,
            "total": len(notifications),
            "unread_only": unread_only
        })

    except Exception as e:
        logger.error(f"Failed to get notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Mark notification as read."""
    try:
        success = await dashboard_generation_service.mark_notification_read(
            notification_id, current_user
        )

        return CustomJSONResponse(content={
            "success": success,
            "notification_id": notification_id
        })

    except Exception as e:
        logger.error(f"Failed to mark notification as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


# Analytics Endpoints

@router.get("/dashboard/analytics")
async def get_dashboard_analytics(
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard generation and usage analytics."""
    try:
        analytics = await dashboard_generation_service.get_dashboard_analytics()

        return CustomJSONResponse(content=analytics)

    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


# Health Check

@router.get("/dashboard/health")
async def dashboard_generation_health_check():
    """Health check for dashboard generation service."""
    try:
        analytics = await dashboard_generation_service.get_dashboard_analytics()

        return CustomJSONResponse(content={
            "status": "healthy",
            "service": "dashboard_generation",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_dashboards": analytics.get("dashboard_metrics", {}).get("total_dashboards", 0),
                "active_generations": analytics.get("generation_metrics", {}).get("total_generations", 0),
                "success_rate": analytics.get("generation_metrics", {}).get("success_rate", 0)
            }
        })

    except Exception as e:
        logger.error(f"Dashboard generation health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard generation service unhealthy: {str(e)}"
        )
