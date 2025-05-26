import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from fastapi.responses import JSONResponse


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


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and pandas objects"""
    def default(self, obj):
        return make_json_serializable(obj)


class CustomJSONResponse(JSONResponse):
    """Custom JSONResponse that uses our serializer"""
    def render(self, content: Any) -> bytes:
        return json.dumps(
            make_json_serializable(content),
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
