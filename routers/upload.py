import uuid
from datetime import datetime

import pandas as pd
from config.settings import dashboards_storage
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from models.upload import UploadResponse
from services.dashboard_service import DashboardService
from services.data_analysis import analyze_excel_data
from utils.file_handling import save_uploaded_file, validate_excel_file
from utils.serialization import make_json_serializable

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload and process Excel file to generate dashboard"""
    try:
        # Validate file
        validate_excel_file(file)

        # Save file
        file_path = save_uploaded_file(file)

        # Analyze data
        analysis = analyze_excel_data(file_path)
        df = pd.read_excel(file_path)

        # Generate dashboard using LLM
        dashboard_service = DashboardService()
        dashboard_config = await dashboard_service.generate_llm_dashboard(df, analysis, file.filename or "Unknown")

        print(f"Dashboard config generated:")
        print(dashboard_config)

        # Create dashboard ID
        dashboard_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        # Ensure all data is JSON serializable before storage
        serializable_config = make_json_serializable(dashboard_config.dict())

        # Store dashboard in memory (TODO: Save to database)
        dashboards_storage[dashboard_id] = make_json_serializable({
            "dashboard_id": dashboard_id,
            "dashboard_config": serializable_config,
            "status": "ready",
            "created_at": created_at,
            "file_url": f"/uploads/{file_path.name}"
        })

        # Create response with serialized data
        response = UploadResponse(
            status="success",
            dashboard_id=dashboard_id,
            dashboard_config=dashboard_config,
            file_url=f"/uploads/{file_path.name}",
            created_at=created_at
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
