from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

from .dashboard import DashboardConfig


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
