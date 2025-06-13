import uuid
from datetime import datetime

import pandas as pd
from database.connection import get_db
from database.models import User
from dependencies.auth import get_current_active_user
from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, UploadFile)
from models.upload import UploadResponse
from services.dashboard_service import DashboardService
from services.data_analysis import analyze_excel_data
from services.database_service import DatabaseService
from sqlalchemy.orm import Session
from utils.file_handling import save_uploaded_file, validate_excel_file

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    category: str = Form(None),
    chart_types: str = Form(None),
    number_of_charts: str = Form(None),
    description: str = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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

        # Process user inputs for generation
        generation_options = {
            "category": category,
            "chart_types": chart_types.split(",") if chart_types else [],
            "number_of_charts": int(number_of_charts) if number_of_charts else 3,
            "description": description
        }

        # Generate dashboard using LLM
        dashboard_service = DashboardService()
        dashboard_config = await dashboard_service.generate_llm_dashboard(
            df, analysis, file.filename or "Unknown", generation_options
        )

        print(f"Dashboard config generated for user {current_user.username}:")
        print(dashboard_config)

        # Create dashboard ID
        dashboard_id = str(uuid.uuid4())
        file_url = f"/uploads/{file_path.name}"

        # Save to database with user association
        db_service = DatabaseService(db)
        db_dashboard = db_service.create_dashboard(
            dashboard_id=dashboard_id,
            dashboard_config=dashboard_config,
            user=current_user,
            file_url=file_url
        )

        # Create response
        response = UploadResponse(
            status="success",
            dashboard_id=dashboard_id,
            dashboard_config=dashboard_config,
            file_url=file_url,
            created_at=db_dashboard.created_at.isoformat()
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
