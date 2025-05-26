from config.settings import dashboards_storage
from fastapi import APIRouter, HTTPException
from utils.serialization import CustomJSONResponse

router = APIRouter()


@router.get("/dashboard/{dashboard_id}")
def get_dashboard(dashboard_id: str):
    """Get dashboard configuration by ID"""
    if dashboard_id not in dashboards_storage:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return CustomJSONResponse(content=dashboards_storage[dashboard_id])
