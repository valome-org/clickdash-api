from .dashboard import router as dashboard_router
from .models import router as models_router
from .upload import router as upload_router

__all__ = ["dashboard_router", "upload_router", "models_router"]
