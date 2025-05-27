from database.connection import get_db
from fastapi import APIRouter, Depends, HTTPException
from services.database_service import DatabaseService
from sqlalchemy.orm import Session
from utils.serialization import CustomJSONResponse

router = APIRouter()


@router.get("/dashboard/{dashboard_id}")
def get_dashboard(dashboard_id: str, db: Session = Depends(get_db)):
    """Get dashboard configuration by ID"""
    db_service = DatabaseService(db)
    dashboard = db_service.get_dashboard(dashboard_id)

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return CustomJSONResponse(content=dashboard.to_dict())


@router.get("/dashboards")
def list_dashboards(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all dashboards with pagination"""
    db_service = DatabaseService(db)
    dashboards = db_service.list_dashboards(limit=limit, offset=offset)

    return CustomJSONResponse(content={
        "dashboards": [dashboard.to_dict() for dashboard in dashboards],
        "total": len(dashboards)
    })
