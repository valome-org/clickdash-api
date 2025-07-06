from typing import List

from database.connection import get_db
from database.models import User
from dependencies.auth import get_current_active_user
from fastapi import APIRouter, Depends, HTTPException
from services.database_service import DatabaseService
from sqlalchemy.orm import Session
from utils.serialization import CustomJSONResponse

router = APIRouter()


@router.get("/dashboard/{dashboard_id}")
def get_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard configuration by ID (user can only access their own dashboards)"""
    db_service = DatabaseService(db)
    dashboard = db_service.get_dashboard(dashboard_id, current_user)

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return CustomJSONResponse(content=dashboard.to_dict())


@router.get("/dashboards/my")
def get_my_dashboards(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's dashboards with pagination"""
    db_service = DatabaseService(db)
    dashboards = db_service.get_user_dashboards(current_user, limit=limit, offset=offset)

    return CustomJSONResponse(content={
        "dashboards": [dashboard.to_dict() for dashboard in dashboards],
        "total": len(dashboards),
        "user_id": current_user.user_id
    })


@router.get("/dashboards")
def list_all_dashboards(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all dashboards with pagination (admin only)"""
    db_service = DatabaseService(db)
    dashboards = db_service.list_dashboards(limit=limit, offset=offset)

    return CustomJSONResponse(content={
        "dashboards": [dashboard.to_dict() for dashboard in dashboards],
        "total": len(dashboards)
    })


@router.delete("/dashboard/{dashboard_id}")
def delete_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a dashboard (user can only delete their own dashboards)"""
    db_service = DatabaseService(db)
    success = db_service.delete_dashboard(dashboard_id, current_user)

    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return CustomJSONResponse(content={
        "message": "Dashboard deleted successfully",
        "dashboard_id": dashboard_id
    })
