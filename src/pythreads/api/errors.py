from __future__ import annotations

from json import JSONEncoder
from typing import Any


class ThreadsInvalidParameter(ValueError):
    ...


class ThreadsResponseError(Exception):
    def __init__(self, response: dict) -> None:
        super().__init__(JSONEncoder().encode(response))
        self.response = response


class ThreadsHTTPError(Exception):
    def __init__(self, status: int, body: Any) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body

