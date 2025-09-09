from __future__ import annotations

from datetime import datetime, date
from typing import Any, AsyncIterator, Dict, Iterable, Optional, Union


def ts_to_str(dt: datetime) -> str:
    return str(int(dt.timestamp()))


def iso_date_or_str(d: date | str) -> str:
    return d if isinstance(d, str) else d.isoformat()


def str_params(params: Dict[str, Any]) -> Dict[str, str]:
    return {k: str(v) for k, v in params.items()}


class PaginatedIterator:
    """Base class for paginated API iterators to reduce code duplication."""
    
    def __init__(
        self,
        transport,
        endpoint: str,
        fields: Iterable[str],
        per_page: int = 25,
        page_limit: Optional[int] = None,
        **kwargs: Any
    ):
        self.transport = transport
        self.endpoint = endpoint
        self.fields = fields
        self.per_page = per_page
        self.page_limit = page_limit
        self.extra_params = kwargs
        self.pages = 0
        self.after: Optional[str] = None
    
    def _build_params(self) -> Dict[str, str]:
        """Build base pagination parameters. Override for endpoint-specific params."""
        from .types import PARAMS__FIELDS, PARAMS__LIMIT, PARAMS__AFTER
        
        params: Dict[str, str] = {
            PARAMS__FIELDS: ",".join(self.fields),
            PARAMS__LIMIT: str(self.per_page)
        }
        
        if self.after:
            params[PARAMS__AFTER] = self.after
        
        # Add any extra parameters
        for key, value in self.extra_params.items():
            if value is not None:
                if isinstance(value, (date, datetime)):
                    params[key] = iso_date_or_str(value)
                else:
                    params[key] = str(value)
        
        return params
    
    async def __aiter__(self) -> AsyncIterator[Dict[str, Any]]:
        """Async iterator implementation."""
        while True:
            params = self._build_params()
            response = await self.transport.get(self.endpoint, params)
            
            for item in response.get("data", []):
                yield item
            
            self.pages += 1
            if self.page_limit is not None and self.pages >= self.page_limit:
                break
            
            self.after = response.get("paging", {}).get("cursors", {}).get("after")
            if not self.after:
                break

