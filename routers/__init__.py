from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .models import router as models_router
from .upload import router as upload_router

__all__ = ["auth_router", "dashboard_router", "upload_router", "models_router"]
