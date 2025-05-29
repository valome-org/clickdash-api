from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class KeyMetric(BaseModel):
    """Key metrics to display on dashboard"""
    metric: str
    value: str
    description: Optional[str] = None


class ChartConfig(BaseModel):
    """Configuration for an individual chart"""
    chart_type: str
    title: str
    x_axis: str
    y_axis: str
    data: Dict[str, Any]
    insights: Optional[str] = None
    color_scheme: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    interactive_features: Optional[List[str]] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            pd.Timestamp: lambda ts: ts.isoformat(),
            np.integer: lambda x: int(x),
            np.floating: lambda x: float(x),
            np.ndarray: lambda x: x.tolist()
        }


class DashboardConfig(BaseModel):
    """Configuration for the entire dashboard"""
    title: str
    charts: List[ChartConfig]
    insights: str
    summary: str
    key_metrics: List[KeyMetric]
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            pd.Timestamp: lambda ts: ts.isoformat(),
            np.integer: lambda x: int(x),
            np.floating: lambda x: float(x),
            np.ndarray: lambda x: x.tolist()
        }
