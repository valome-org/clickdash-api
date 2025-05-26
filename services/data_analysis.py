from pathlib import Path

import pandas as pd
from fastapi import HTTPException
from utils.serialization import make_json_serializable


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
