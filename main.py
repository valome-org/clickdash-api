from datetime import datetime

from config.settings import (APP_DESCRIPTION, APP_TITLE, APP_VERSION,
                             CORS_ORIGINS, UPLOAD_DIR)
from database import create_tables
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import auth_router, dashboard_router, models_router, upload_router, data_sources_router, processing_router
from routers.validation import router as validation_router
from routers.cleanup import router as cleanup_router
from routers.metadata import router as metadata_router
from utils.serialization import CustomJSONResponse

# Initialize database tables
create_tables()

# Create FastAPI app with custom JSON response
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    default_response_class=CustomJSONResponse,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

# Add CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(models_router, prefix="/api", tags=["models"])
app.include_router(data_sources_router, prefix="/api", tags=["data-sources"])
app.include_router(processing_router, prefix="/api", tags=["processing"])
app.include_router(validation_router)
app.include_router(cleanup_router)
app.include_router(metadata_router)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return CustomJSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": APP_VERSION
    })


@app.get("/")
async def read_root():
    """Root endpoint"""
    return {
        "message": "Excel Dashboard AI API",
        "version": APP_VERSION,
        "status": "running",
        "authentication": "enabled"
    }
