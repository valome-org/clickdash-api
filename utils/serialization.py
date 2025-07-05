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
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        # Handle NaN and infinity values in numpy floats
        if np.isnan(obj) or np.isinf(obj):
            return None
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
    elif isinstance(obj, (int, str, bool)):
        return obj
    elif isinstance(obj, float):
        # Handle NaN and infinity values in regular floats
        if np.isnan(obj) or np.isinf(obj):
            return None
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
        try:
            return json.dumps(
                make_json_serializable(content),
                ensure_ascii=False,
                allow_nan=False,  # Explicitly disallow NaN values
                indent=None,
                separators=(",", ":"),
            ).encode("utf-8")
        except (ValueError, TypeError) as e:
            # If serialization fails, return error info
            error_content = {
                "error": "JSON serialization failed",
                "details": str(e),
                "content_type": str(type(content))
            }
            return json.dumps(error_content).encode("utf-8")
