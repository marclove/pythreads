from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Dict, Optional

import aiohttp

from pythreads.credentials import Credentials
from pythreads.threads import Threads, ThreadsAccessTokenExpired

from .errors import ThreadsHTTPError

logger = logging.getLogger(__name__)


class Transport:
    """HTTP transport for the Threads API.

    Handles URL building, access token validation, retries/backoff, and
    JSON/text parsing with consistent error handling.
    """

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        credentials: Credentials,
        timeout: Optional[float | aiohttp.ClientTimeout] = 30,
        base_url: Optional[str] = None,
        retries: int = 0,
        backoff_base: float = 0.5,
        backoff_max: float = 4.0,
    ) -> None:
        self.session = session
        self.credentials = credentials
        self.timeout = timeout
        self.base_url = base_url
        self.retries = max(0, int(retries))
        self.backoff_base = float(backoff_base)
        self.backoff_max = float(backoff_max)

    def _access_token(self) -> str:
        if self.credentials.expired():
            raise ThreadsAccessTokenExpired()
        return self.credentials.access_token

    def _build_url(self, path: str, params: Dict[str, Any]) -> str:
        access_token = self._access_token()
        if self.base_url:
            return Threads.build_graph_api_url(path, params, access_token, self.base_url)
        return Threads.build_graph_api_url(path, params, access_token)

    async def _request_url(self, method: str, url: str) -> Any:
        http_method = getattr(self.session, method)
        attempts = self.retries + 1
        for i in range(1, attempts + 1):
            async with http_method(url) as response:
                status = getattr(response, "status", 200)
                if isinstance(status, int) and status >= 400:
                    should_retry = status == 429 or 500 <= status <= 599
                    if should_retry and i <= self.retries:
                        delay = min(
                            self.backoff_base * (2 ** (i - 1)) + random.uniform(0, 0.1),
                            self.backoff_max,
                        )
                        logger.debug(
                            "Transient error %s on %s %s, retry %s/%s in %.2fs",
                            status,
                            method.upper(),
                            url,
                            i,
                            self.retries,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    try:
                        body = await response.json()
                    except Exception:
                        try:
                            body = await response.text()
                        except Exception:
                            body = None
                    logger.debug("Request failed: %s %s -> %s", method.upper(), url, status)
                    raise ThreadsHTTPError(status, body)
                return await response.json()

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = self._build_url(path, params or {})
        return await self._request_url("get", url)

    async def post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = self._build_url(path, params or {})
        return await self._request_url("post", url)

