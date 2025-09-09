from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict


def ts_to_str(dt: datetime) -> str:
    return str(int(dt.timestamp()))


def iso_date_or_str(d: date | str) -> str:
    return d if isinstance(d, str) else d.isoformat()


def str_params(params: Dict[str, Any]) -> Dict[str, str]:
    return {k: str(v) for k, v in params.items()}

