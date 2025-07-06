import uuid
from datetime import datetime

import pandas as pd
from database.connection import get_db
from database.models import User
from dependencies.auth import get_current_active_user
from fastapi import (APIRouter, Depends, File, Form,
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process Excel file to generate dashboard with comprehensive error handling"""
    file_path = None

    try:
        # Basic input validation
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided"
            )

        # Validate file before processing
        validate_excel_file(file)

        # Save file with validation
        file_path = save_uploaded_file(file)

        # Determine file type for appropriate reading
        file_extension = file_path.suffix.lower()

        try:
            if file_extension == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
        except Exception as e:
            # Clean up uploaded file on read error
            if file_path and file_path.exists():
                file_path.unlink()

            if "corrupted" in str(e).lower() or "invalid" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail="File appears to be corrupted or invalid. Please try uploading again."
                )
            elif "password" in str(e).lower() or "protected" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected files are not supported. Please remove protection and try again."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unable to read file: {str(e)}"
                )

        # Validate dataframe content
        if df.empty:
            if file_path and file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail="File contains no data. Please upload a file with data rows."
            )

        if len(df.columns) == 0:
            if file_path and file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail="File has no columns. Please ensure your file has proper headers."
            )

        # Validate user inputs
        try:
            num_charts = int(number_of_charts) if number_of_charts else 3
            if num_charts < 1 or num_charts > 10:
                raise HTTPException(
                    status_code=400,
                    detail="Number of charts must be between 1 and 10"
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid number of charts specified"
            )

        # Process chart types
        processed_chart_types = []
        if chart_types:
            valid_chart_types = ['bar', 'line', 'pie', 'scatter', 'area', 'doughnut', 'radar', 'heatmap']
            chart_type_list = [ct.strip().lower() for ct in chart_types.split(",")]
            processed_chart_types = [ct for ct in chart_type_list if ct in valid_chart_types]

        # Analyze data with error handling
        try:
            analysis = analyze_excel_data(file_path)
        except Exception as e:
            # Keep file for dashboard generation but note analysis error
            print(f"Analysis warning for user {current_user.username}: {str(e)}")
            analysis = {"error": "Analysis partially failed", "summary": "Basic processing completed"}

        # Process user inputs for generation
        generation_options = {
            "category": category,
            "chart_types": processed_chart_types,
            "number_of_charts": num_charts,
            "description": description
        }

        # Generate dashboard using LLM with error handling
        try:
            dashboard_service = DashboardService()
            dashboard_config = await dashboard_service.generate_llm_dashboard(
                df, analysis, file.filename or "Unknown", generation_options
            )
        except Exception as e:
            # Clean up on dashboard generation failure
            if file_path and file_path.exists():
                file_path.unlink()

            if "rate limit" in str(e).lower():
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily busy. Please try again in a few moments."
                )
            elif "timeout" in str(e).lower():
                raise HTTPException(
                    status_code=504,
                    detail="Dashboard generation timed out. Please try with a smaller file or simpler options."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate dashboard. Please try again or contact support."
                )

        print(f"Dashboard config generated for user {current_user.username}:")
        print(dashboard_config)

        # Create dashboard ID
        dashboard_id = str(uuid.uuid4())
        file_url = f"/uploads/{file_path.name}"

        # Save to database with error handling
        try:
            db_service = DatabaseService(db)
            db_dashboard = db_service.create_dashboard(
                dashboard_id=dashboard_id,
                dashboard_config=dashboard_config,
                user=current_user,
                file_url=file_url
            )
        except Exception as e:
            # Clean up on database save failure
            if file_path and file_path.exists():
                file_path.unlink()

            print(f"Database error for user {current_user.username}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save dashboard. Please try again."
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
        # Clean up on any HTTP exception
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass  # Best effort cleanup
        raise
    except Exception as e:
        # Clean up on any unexpected error
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass  # Best effort cleanup

        print(f"Unexpected upload error for user {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during file processing. Please try again."
        )
