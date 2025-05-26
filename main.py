import asyncio
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import numpy as np
import openpyxl
import pandas as pd
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

def make_json_serializable(obj):
    """Convert pandas/numpy objects to JSON serializable types"""
    if obj is None:
        return None
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return [make_json_serializable(x) for x in obj.tolist()]
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):  # Any datetime-like object
        return obj.isoformat()
    elif isinstance(obj, (pd.Series, pd.Index)):
        return [make_json_serializable(x) for x in obj.tolist()]
    elif isinstance(obj, list):
        return [make_json_serializable(x) for x in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(x) for x in obj]
    elif isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (int, float, str, bool)):
        return obj
    elif pd.isna(obj):  # Handle pandas NaN values
        return None
    else:
        return str(obj)  # Fallback to string representation

# Custom JSON encoder for datetime and pandas objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        return make_json_serializable(obj)

# Custom JSONResponse that uses our serializer
class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            make_json_serializable(content),
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app = FastAPI(
    title="Excel Dashboard AI API",
    description="Convert Excel files to interactive dashboards using AI",
    version="1.0.0",
    default_response_class=CustomJSONResponse
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

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "gemini").lower()

# Initialize LLM clients
openai_client = None
if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your-openai-api-key-here":
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here":
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Models
class ChartConfig(BaseModel):
    chart_type: str
    title: str
    x_axis: str
    y_axis: str
    data: dict
    insights: Optional[str] = None
    color_scheme: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            pd.Timestamp: lambda ts: ts.isoformat(),
            np.integer: lambda x: int(x),
            np.floating: lambda x: float(x),
            np.ndarray: lambda x: x.tolist()
        }

class DashboardConfig(BaseModel):
    title: str
    charts: list[ChartConfig]
    insights: str
    summary: str
    key_metrics: List[Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            pd.Timestamp: lambda ts: ts.isoformat(),
            np.integer: lambda x: int(x),
            np.floating: lambda x: float(x),
            np.ndarray: lambda x: x.tolist()
        }

class UploadResponse(BaseModel):
    status: str
    dashboard_id: str
    dashboard_config: DashboardConfig
    file_url: Optional[str] = None
    created_at: str

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            pd.Timestamp: lambda ts: ts.isoformat(),
            np.integer: lambda x: int(x),
            np.floating: lambda x: float(x),
            np.ndarray: lambda x: x.tolist()
        }

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

        # Basic data analysis with proper serialization
        summary_dict = df.describe(include='all').fillna('').to_dict()
        missing_values = df.isnull().sum().to_dict()
        data_types = df.dtypes.astype(str).to_dict()

        # Serialize all potentially problematic objects
        analysis = {
            "columns": list(df.columns),
            "rows": len(df),
            "numeric_columns": list(df.select_dtypes(include=['number']).columns),
            "categorical_columns": list(df.select_dtypes(include=['object']).columns),
            "summary": make_json_serializable(summary_dict),
            "missing_values": make_json_serializable(missing_values),
            "data_types": make_json_serializable(data_types)
        }

        return analysis

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze Excel file: {str(e)}"
        )

async def analyze_data_with_llm(df: pd.DataFrame, analysis: dict, filename: str) -> Dict[str, Any]:
    """Use OpenAI or Gemini to analyze data and generate intelligent insights and chart recommendations"""

    # Prepare data summary for LLM with proper serialization
    sample_data = df.head(5).to_dict() if len(df) > 0 else {}

    data_summary = {
        "filename": filename,
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": {
            "numeric": analysis['numeric_columns'],
            "categorical": analysis['categorical_columns'],
            "all_columns": analysis['columns']
        },
        "sample_data": make_json_serializable(sample_data),
        "data_types": analysis['data_types'],
        "missing_values": analysis['missing_values'],
        "basic_stats": {}
    }

    # Add statistical summaries for numeric columns
    for col in analysis['numeric_columns']:
        if col in df.columns:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                data_summary["basic_stats"][col] = make_json_serializable({
                    "mean": col_data.mean(),
                    "median": col_data.median(),
                    "std": col_data.std() if len(col_data) > 1 else 0,
                    "min": col_data.min(),
                    "max": col_data.max(),
                    "unique_count": col_data.nunique()
                })

    # Add categorical summaries
    for col in analysis['categorical_columns'][:3]:  # Limit to first 3 categorical columns
        if col in df.columns:
            value_counts = df[col].value_counts().head(10)
            data_summary["basic_stats"][col] = make_json_serializable({
                "top_values": value_counts.to_dict(),
                "unique_count": df[col].nunique(),
                "most_common": value_counts.index[0] if len(value_counts) > 0 else None
            })

    prompt = f"""
    You are a data visualization expert. Analyze this Excel dataset and create an intelligent dashboard configuration.

    Dataset Summary:
    {json.dumps(data_summary, indent=2, cls=CustomJSONEncoder)}

    Requirements:
    1. Generate 3-5 meaningful charts that tell a story about the data
    2. Choose appropriate chart types based on data characteristics
    3. Create insightful titles and descriptions
    4. Provide key business insights
    5. Suggest color schemes that enhance readability
    6. Focus on the most important patterns and relationships

    Return your response as a JSON object with this exact structure:
    {{
        "dashboard_title": "Meaningful title for the dashboard",
        "summary": "Brief 2-3 sentence summary of what the data represents",
        "key_metrics": [
            {{"metric": "Metric Name", "value": "Value", "description": "What this means"}},
            {{"metric": "Another Metric", "value": "Value", "description": "What this means"}}
        ],
        "charts": [
            {{
                "chart_type": "bar|line|pie|scatter|area",
                "title": "Descriptive chart title",
                "x_axis": "column_name",
                "y_axis": "column_name_or_aggregation",
                "insights": "What this chart reveals about the data",
                "color_scheme": "primary|secondary|success|warning|info",
                "data_config": {{
                    "source_columns": ["col1", "col2"],
                    "aggregation": "sum|count|avg|none",
                    "limit": 10,
                    "sort": "asc|desc"
                }}
            }}
        ],
        "insights": "Detailed insights about the data patterns, trends, and business implications (3-4 sentences)"
    }}

    Important:
    - Only reference columns that actually exist in the dataset
    - Choose chart types that make sense for the data types
    - Ensure x_axis and y_axis reference actual column names
    - Make titles business-friendly, not technical
    - Focus on actionable insights
    """

    try:
        # Try primary model first (from environment configuration)
        if LLM_MODEL == "gemini" and os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here":
            return await analyze_with_gemini(prompt)
        elif LLM_MODEL == "openai" and openai_client:
            return await analyze_with_openai(prompt)
        # Fallback to available model
        elif os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here":
            return await analyze_with_gemini(prompt)
        elif openai_client:
            return await analyze_with_openai(prompt)
        else:
            print("No LLM API keys configured, using fallback analysis")
            return generate_fallback_analysis(df, analysis, filename)

    except Exception as e:
        print(f"LLM Analysis error: {str(e)}")
        # Fallback to basic analysis
        return generate_fallback_analysis(df, analysis, filename)

async def analyze_with_openai(prompt: str) -> Dict[str, Any]:
    """Analyze data using OpenAI GPT"""
    if not openai_client:
        raise Exception("OpenAI client not configured")

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a data visualization expert who creates insightful, business-focused dashboards. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )

    response_text = response.choices[0].message.content.strip()

    # Clean up the response to ensure it's valid JSON
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    parsed_response = json.loads(response_text)
    return make_json_serializable(parsed_response)

async def analyze_with_gemini(prompt: str) -> Dict[str, Any]:
    """Analyze data using Google Gemini"""
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-google-api-key-here":
        raise Exception("Google API key not configured")

    # Initialize Gemini model
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Create system prompt for Gemini
    full_prompt = f"""
    You are a data visualization expert who creates insightful, business-focused dashboards.
    You must respond ONLY with valid JSON, no other text or formatting.

    {prompt}
    """

    response = model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2000,
        )
    )

    response_text = response.text.strip()

    # Clean up the response to ensure it's valid JSON
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    parsed_response = json.loads(response_text)
    return make_json_serializable(parsed_response)

def generate_fallback_analysis(df: pd.DataFrame, analysis: dict, filename: str) -> Dict[str, Any]:
    """Fallback analysis when LLM is not available"""
    return make_json_serializable({
        "dashboard_title": f"Analysis of {filename}",
        "summary": f"Dataset contains {len(df)} rows and {len(df.columns)} columns with various data types.",
        "key_metrics": [
            {"metric": "Total Rows", "value": str(len(df)), "description": "Number of records in the dataset"},
            {"metric": "Columns", "value": str(len(df.columns)), "description": "Number of data fields"}
        ],
        "charts": [
            {
                "chart_type": "bar",
                "title": f"Distribution of {analysis['categorical_columns'][0]}" if analysis['categorical_columns'] else "Data Overview",
                "x_axis": analysis['categorical_columns'][0] if analysis['categorical_columns'] else "Categories",
                "y_axis": "Count",
                "insights": "Basic distribution of categorical data",
                "color_scheme": "primary",
                "data_config": {
                    "source_columns": [analysis['categorical_columns'][0]] if analysis['categorical_columns'] else [],
                    "aggregation": "count",
                    "limit": 10,
                    "sort": "desc"
                }
            }
        ],
        "insights": "This dataset provides various data points that can be analyzed for business insights. Further analysis could reveal patterns and trends."
    })

def generate_chart_data(df: pd.DataFrame, chart_config: dict) -> dict:
    """Generate actual chart data based on LLM recommendations"""
    try:
        chart_type = chart_config.get("chart_type", "bar")
        data_config = chart_config.get("data_config", {})
        source_columns = data_config.get("source_columns", [])
        aggregation = data_config.get("aggregation", "count")
        limit = data_config.get("limit", 10)
        sort_order = data_config.get("sort", "desc")

        if not source_columns or not all(col in df.columns for col in source_columns):
            # Fallback to first available columns
            if chart_type in ["bar", "pie"] and len(df.select_dtypes(include=['object']).columns) > 0:
                source_columns = [df.select_dtypes(include=['object']).columns[0]]
                aggregation = "count"
            elif len(df.select_dtypes(include=['number']).columns) > 0:
                source_columns = [df.select_dtypes(include=['number']).columns[0]]
                aggregation = "sum"
            else:
                return {"labels": ["No Data"], "datasets": [{"data": [0]}]}

        if chart_type in ["bar", "pie"]:
            # Categorical data aggregation
            if aggregation == "count":
                result = df[source_columns[0]].value_counts().head(limit)
            else:
                result = df.groupby(source_columns[0])[source_columns[1]].agg(aggregation).head(limit) if len(source_columns) > 1 else df[source_columns[0]].value_counts().head(limit)

            if sort_order == "asc":
                result = result.sort_values()

            # Convert to JSON serializable format
            labels = make_json_serializable(result.index.tolist())
            values = make_json_serializable(result.values.tolist())

            # Color schemes
            color_schemes = {
                "primary": ["rgba(59, 130, 246, 0.8)", "rgba(99, 102, 241, 0.8)", "rgba(139, 92, 246, 0.8)"],
                "secondary": ["rgba(107, 114, 128, 0.8)", "rgba(156, 163, 175, 0.8)", "rgba(209, 213, 219, 0.8)"],
                "success": ["rgba(34, 197, 94, 0.8)", "rgba(22, 163, 74, 0.8)", "rgba(21, 128, 61, 0.8)"],
                "warning": ["rgba(245, 158, 11, 0.8)", "rgba(217, 119, 6, 0.8)", "rgba(180, 83, 9, 0.8)"],
                "info": ["rgba(6, 182, 212, 0.8)", "rgba(14, 165, 233, 0.8)", "rgba(37, 99, 235, 0.8)"]
            }

            scheme = chart_config.get("color_scheme", "primary")
            colors = color_schemes.get(scheme, color_schemes["primary"])

            return make_json_serializable({
                "labels": labels,
                "datasets": [{
                    "label": chart_config.get("title", "Data"),
                    "data": values,
                    "backgroundColor": colors * (len(values) // len(colors) + 1),
                    "borderColor": [c.replace("0.8", "1") for c in colors] * (len(values) // len(colors) + 1),
                    "borderWidth": 1
                }]
            })

        elif chart_type == "line":
            # Time series or sequential data
            column = source_columns[0]
            data = df[column].dropna().head(limit)

            return make_json_serializable({
                "labels": [str(i) for i in range(len(data))],
                "datasets": [{
                    "label": column,
                    "data": data.tolist(),
                    "borderColor": "rgba(34, 197, 94, 1)",
                    "backgroundColor": "rgba(34, 197, 94, 0.1)",
                    "tension": 0.4
                }]
            })

        elif chart_type == "scatter":
            # Two numeric columns
            if len(source_columns) >= 2:
                x_data = df[source_columns[0]].dropna()
                y_data = df[source_columns[1]].dropna()
                min_len = min(len(x_data), len(y_data))

                scatter_data = []
                for i in range(min_len):
                    scatter_data.append({
                        "x": make_json_serializable(x_data.iloc[i]),
                        "y": make_json_serializable(y_data.iloc[i])
                    })

                return {
                    "datasets": [{
                        "label": f"{source_columns[0]} vs {source_columns[1]}",
                        "data": scatter_data,
                        "backgroundColor": "rgba(59, 130, 246, 0.6)"
                    }]
                }

        # Default fallback
        return {"labels": ["No Data"], "datasets": [{"data": [0]}]}

    except Exception as e:
        print(f"Chart data generation error: {str(e)}")
        return {"labels": ["Error"], "datasets": [{"data": [0]}]}

async def generate_llm_dashboard(df: pd.DataFrame, analysis: dict, filename: str) -> DashboardConfig:
    """Generate complete dashboard using LLM analysis"""
    try:
        # Get LLM analysis
        llm_analysis = await analyze_data_with_llm(df, analysis, filename)

        # Generate charts based on LLM recommendations
        charts = []
        for chart_spec in llm_analysis.get("charts", []):
            chart_data = generate_chart_data(df, chart_spec)

            chart = ChartConfig(
                chart_type=chart_spec.get("chart_type", "bar"),
                title=chart_spec.get("title", "Chart"),
                x_axis=chart_spec.get("x_axis", "X"),
                y_axis=chart_spec.get("y_axis", "Y"),
                data=chart_data,
                insights=chart_spec.get("insights", ""),
                color_scheme=chart_spec.get("color_scheme", "primary")
            )
            charts.append(chart)

        dashboard_config = DashboardConfig(
            title=llm_analysis.get("dashboard_title", f"Dashboard - {filename}"),
            charts=charts,
            insights=llm_analysis.get("insights", ""),
            summary=llm_analysis.get("summary", ""),
            key_metrics=make_json_serializable(llm_analysis.get("key_metrics", []))
        )

        return dashboard_config

    except Exception as e:
        print(f"LLM Dashboard generation error: {str(e)}")
        # Fallback to basic dashboard
        return generate_basic_dashboard(df, analysis, filename)

def generate_basic_dashboard(df: pd.DataFrame, analysis: dict, filename: str) -> DashboardConfig:
    """Fallback dashboard generation"""
    charts = []

    # Basic bar chart for categorical data
    if analysis['categorical_columns']:
        cat_col = analysis['categorical_columns'][0]
        value_counts = df[cat_col].value_counts().head(10)

        chart_data = make_json_serializable({
            "labels": value_counts.index.tolist(),
            "datasets": [{
                "label": "Count",
                "data": value_counts.values.tolist(),
                "backgroundColor": "rgba(59, 130, 246, 0.5)"
            }]
        })

        charts.append(ChartConfig(
            chart_type="bar",
            title=f"Distribution of {cat_col}",
            x_axis=cat_col,
            y_axis="Count",
            data=chart_data,
            insights=f"Shows the distribution of {cat_col} values in the dataset"
        ))

    return DashboardConfig(
        title=f"Basic Dashboard - {filename}",
        charts=charts,
        insights="Basic dashboard with fundamental data visualizations",
        summary=f"Analysis of {filename} containing {len(df)} rows and {len(df.columns)} columns",
        key_metrics=make_json_serializable([
            {"metric": "Total Records", "value": str(len(df)), "description": "Number of data rows"},
            {"metric": "Data Fields", "value": str(len(df.columns)), "description": "Number of columns"}
        ])
    )

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

        # Generate dashboard using LLM
        dashboard_config = await generate_llm_dashboard(df, analysis, file.filename or "Unknown")

        print(f"Dashboard config generated using {LLM_MODEL.upper()} model:")
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

@app.get("/dashboard/{dashboard_id}")
def get_dashboard(dashboard_id: str):
    """Get dashboard configuration by ID"""
    if dashboard_id not in dashboards_storage:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return CustomJSONResponse(content=dashboards_storage[dashboard_id])

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return CustomJSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.get("/")
async def read_root():
    return {"message": "Excel Dashboard AI API", "version": "1.0.0"}

@app.get("/api/models/status")
async def get_model_status():
    """Get current model configuration and availability"""
    return {
        "current_model": LLM_MODEL,
        "available_models": {
            "openai": {
                "configured": openai_client is not None,
                "api_key_set": os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "your-openai-api-key-here"
            },
            "gemini": {
                "configured": os.getenv("GOOGLE_API_KEY") is not None and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here",
                "api_key_set": os.getenv("GOOGLE_API_KEY") is not None and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here"
            }
        }
    }

@app.post("/api/models/switch")
async def switch_model(request: dict):
    """Switch between available models"""
    global LLM_MODEL

    new_model = request.get("model", "").lower()
    if new_model not in ["openai", "gemini"]:
        raise HTTPException(status_code=400, detail="Invalid model. Choose 'openai' or 'gemini'")

    # Check if the requested model is available
    if new_model == "openai" and not openai_client:
        raise HTTPException(status_code=400, detail="OpenAI is not configured. Please set OPENAI_API_KEY")

    if new_model == "gemini" and (not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-google-api-key-here"):
        raise HTTPException(status_code=400, detail="Gemini is not configured. Please set GOOGLE_API_KEY")

    LLM_MODEL = new_model
    return {"message": f"Model switched to {new_model}", "current_model": LLM_MODEL}
