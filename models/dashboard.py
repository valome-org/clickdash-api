from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel


class ChartConfig(BaseModel):
    chart_type: str
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
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
