import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import openpyxl
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Excel Dashboard AI API",
    description="Convert Excel files to interactive dashboards using AI",
    version="1.0.0"
)

# Add CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],  # Add your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# File size limit (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# In-memory storage for dashboards (TODO: Replace with database)
dashboards_storage = {}

# Models
class ChartConfig(BaseModel):
    chart_type: str
    title: str
    x_axis: str
    y_axis: str
    data: dict

class DashboardConfig(BaseModel):
    title: str
    charts: list[ChartConfig]
    insights: str

class UploadResponse(BaseModel):
    status: str
    dashboard_id: str
    dashboard_config: DashboardConfig
    file_url: Optional[str] = None
    created_at: str

def validate_excel_file(file: UploadFile) -> None:
    """Validate uploaded Excel file"""
    # Check file extension
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are allowed"
        )

    # Check content type
    allowed_types = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file."
        )

def save_uploaded_file(file: UploadFile) -> Path:
    """Save uploaded file to disk with proper error handling"""
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename or "file.xlsx").suffix
    filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    try:
        # Save file in chunks to handle large files
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Verify file size
        if file_path.stat().st_size > MAX_FILE_SIZE:
            file_path.unlink()  # Delete the file
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        return file_path

    except Exception as e:
        # Clean up on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

def analyze_excel_data(file_path: Path) -> dict:
    """Analyze Excel file and extract insights"""
    try:
        # Read Excel file
        df = pd.read_excel(file_path)

        if df.empty:
            raise HTTPException(status_code=400, detail="Excel file is empty")

        # Basic data analysis
        analysis = {
            "columns": list(df.columns),
            "rows": len(df),
            "numeric_columns": list(df.select_dtypes(include=['number']).columns),
            "categorical_columns": list(df.select_dtypes(include=['object']).columns),
            "summary": df.describe(include='all').fillna('').to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "data_types": df.dtypes.astype(str).to_dict()
        }

        return analysis

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze Excel file: {str(e)}"
        )

def generate_chart_configs(df: pd.DataFrame, analysis: dict) -> list[ChartConfig]:
    """Generate chart configurations based on data analysis"""
    charts = []

    try:
        # Chart 1: Bar chart for categorical data
        if analysis['categorical_columns']:
            cat_col = analysis['categorical_columns'][0]
            value_counts = df[cat_col].value_counts().head(10)

            charts.append(ChartConfig(
                chart_type="bar",
                title=f"Distribution of {cat_col}",
                x_axis=cat_col,
                y_axis="Count",
                data={
                    "labels": value_counts.index.tolist(),
                    "datasets": [{
                        "label": "Count",
                        "data": value_counts.values.tolist(),
                        "backgroundColor": "rgba(59, 130, 246, 0.5)",
                        "borderColor": "rgba(59, 130, 246, 1)",
                        "borderWidth": 1
                    }]
                }
            ))

        # Chart 2: Line chart for numeric data over index
        if analysis['numeric_columns']:
            num_col = analysis['numeric_columns'][0]
            sample_data = df[num_col].dropna().head(20)

            charts.append(ChartConfig(
                chart_type="line",
                title=f"{num_col} Trend",
                x_axis="Index",
                y_axis=num_col,
                data={
                    "labels": [str(i) for i in sample_data.index.tolist()],
                    "datasets": [{
                        "label": num_col,
                        "data": sample_data.values.tolist(),
                        "borderColor": "rgba(34, 197, 94, 1)",
                        "backgroundColor": "rgba(34, 197, 94, 0.1)",
                        "tension": 0.4
                    }]
                }
            ))

        # Chart 3: Pie chart for categorical distribution
        if analysis['categorical_columns'] and len(analysis['categorical_columns']) > 1:
            cat_col = analysis['categorical_columns'][1] if len(analysis['categorical_columns']) > 1 else analysis['categorical_columns'][0]
            value_counts = df[cat_col].value_counts().head(5)

            charts.append(ChartConfig(
                chart_type="pie",
                title=f"{cat_col} Distribution",
                x_axis=cat_col,
                y_axis="Percentage",
                data={
                    "labels": value_counts.index.tolist(),
                    "datasets": [{
                        "data": value_counts.values.tolist(),
                        "backgroundColor": [
                            "rgba(239, 68, 68, 0.8)",
                            "rgba(59, 130, 246, 0.8)",
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(245, 158, 11, 0.8)",
                            "rgba(139, 92, 246, 0.8)"
                        ]
                    }]
                }
            ))

        return charts

    except Exception as e:
        # Return a default chart if generation fails
        return [ChartConfig(
            chart_type="bar",
            title="Data Overview",
            x_axis="Categories",
            y_axis="Values",
            data={
                "labels": ["No data"],
                "datasets": [{
                    "label": "Count",
                    "data": [0],
                    "backgroundColor": "rgba(59, 130, 246, 0.5)"
                }]
            }
        )]

@app.post("/upload", response_model=UploadResponse)
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

        # Generate chart configurations
        charts = generate_chart_configs(df, analysis)

        # Generate insights
        insights = f"""
        Dashboard generated from {file.filename}:
        • {analysis['rows']} rows of data
        • {len(analysis['columns'])} columns
        • {len(analysis['numeric_columns'])} numeric fields
        • {len(analysis['categorical_columns'])} categorical fields
        """

        # Create dashboard configuration
        dashboard_id = str(uuid.uuid4())
        dashboard_config = DashboardConfig(
            title=f"Dashboard - {file.filename}",
            charts=charts,
            insights=insights.strip()
        )

        # Store dashboard in memory (TODO: Save to database)
        dashboards_storage[dashboard_id] = {
            "dashboard_id": dashboard_id,
            "dashboard_config": dashboard_config,
            "status": "ready",
            "created_at": datetime.now().isoformat(),
            "file_url": f"/uploads/{file_path.name}"
        }

        return UploadResponse(
            status="success",
            dashboard_id=dashboard_id,
            dashboard_config=dashboard_config,
            file_url=f"/uploads/{file_path.name}",
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/dashboard/{dashboard_id}")
def get_dashboard(dashboard_id: str):
    """Get dashboard configuration by ID"""
    if dashboard_id not in dashboards_storage:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return dashboards_storage[dashboard_id]

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Excel Dashboard AI API",
        "docs": "/docs",
        "health": "/health"
    }
