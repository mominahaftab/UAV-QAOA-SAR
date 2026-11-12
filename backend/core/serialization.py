"""Safe JSON serialization utilities for NumPy, dataclasses, enums, and dates."""
import dataclasses
import enum
from datetime import date, datetime
from typing import Any

import numpy as np


def safe_json_serialize(obj: Any) -> Any:
    """Recursively convert NumPy types, dataclasses, enums, and dates to JSON-serializable types."""
    if obj is None:
        return None
    if isinstance(obj, (bool, str, int, float)):
        # Check for NaN / Inf
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        val = float(obj)
        return None if (np.isnan(val) or np.isinf(val)) else val
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [safe_json_serialize(x) for x in obj.tolist()]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, enum.Enum):
        return obj.value
    if dataclasses.is_dataclass(obj):
        return safe_json_serialize(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): safe_json_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [safe_json_serialize(x) for x in obj]
    return str(obj)

