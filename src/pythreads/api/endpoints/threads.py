from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, Optional, Union, AsyncIterator, Any

from pythreads.credentials import Credentials

from ..types import (
    DEFAULT_CONVERSATION_FIELDS,
    DEFAULT_REPLY_FIELDS,
    DEFAULT_THREAD_FIELDS,
    PARAMS__AFTER,
    PARAMS__BEFORE,
    PARAMS__FIELDS,
    PARAMS__LIMIT,
    PARAMS__SINCE,
    PARAMS__UNTIL,
)
from ..utils import iso_date_or_str
from ..transport import Transport


class ThreadsService:
    def __init__(self, transport: Transport, credentials: Credentials) -> None:
        self.transport = transport
        self.credentials = credentials

    async def threads(
        self,
        user_id: str | None = None,
        fields: Iterable[str] = DEFAULT_THREAD_FIELDS,
        since: Optional[Union[date, str]] = None,
        until: Optional[Union[date, str]] = None,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields)}
        if since:
            params[PARAMS__SINCE] = iso_date_or_str(since)
        if until:
            params[PARAMS__UNTIL] = iso_date_or_str(until)
        if limit is not None:
            params[PARAMS__LIMIT] = str(limit)
        if before:
            params[PARAMS__BEFORE] = before
        if after:
            params[PARAMS__AFTER] = after

        uid = user_id or self.credentials.user_id
        return await self.transport.get(f"{uid}/threads", params)

    async def replies(self, thread_id: str, fields: Iterable[str] = DEFAULT_REPLY_FIELDS):
        return await self.transport.get(
            f"{thread_id}/replies", {PARAMS__FIELDS: ",".join(fields)}
        )

    async def conversation(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_CONVERSATION_FIELDS,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields)}
        if before:
            params[PARAMS__BEFORE] = before
        if after:
            params[PARAMS__AFTER] = after
        return await self.transport.get(f"{thread_id}/conversation", params)

    # ---------------------- Iterators (convenience) ----------------------

    async def threads_iter(
        self,
        user_id: str | None = None,
        fields: Iterable[str] = DEFAULT_THREAD_FIELDS,
        since: Optional[Union[date, str]] = None,
        until: Optional[Union[date, str]] = None,
        per_page: int = 25,
        page_limit: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        pages = 0
        after: Optional[str] = None
        while True:
            params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields), PARAMS__LIMIT: str(per_page)}
            if since:
                params[PARAMS__SINCE] = iso_date_or_str(since)
            if until:
                params[PARAMS__UNTIL] = iso_date_or_str(until)
            if after:
                params[PARAMS__AFTER] = after
            uid = user_id or self.credentials.user_id
            resp = await self.transport.get(f"{uid}/threads", params)
            for item in resp.get("data", []):
                yield item
            pages += 1
            if page_limit is not None and pages >= page_limit:
                break
            after = resp.get("paging", {}).get("cursors", {}).get("after")
            if not after:
                break

    async def replies_iter(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_REPLY_FIELDS,
        per_page: int = 25,
        page_limit: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        pages = 0
        after: Optional[str] = None
        while True:
            params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields), PARAMS__LIMIT: str(per_page)}
            if after:
                params[PARAMS__AFTER] = after
            resp = await self.transport.get(f"{thread_id}/replies", params)
            for item in resp.get("data", []):
                yield item
            pages += 1
            if page_limit is not None and pages >= page_limit:
                break
            after = resp.get("paging", {}).get("cursors", {}).get("after")
            if not after:
                break

    async def conversation_iter(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_CONVERSATION_FIELDS,
        per_page: int = 25,
        page_limit: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        pages = 0
        after: Optional[str] = None
        while True:
            params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields), PARAMS__LIMIT: str(per_page)}
            if after:
                params[PARAMS__AFTER] = after
            resp = await self.transport.get(f"{thread_id}/conversation", params)
            for item in resp.get("data", []):
                yield item
            pages += 1
            if page_limit is not None and pages >= page_limit:
                break
            after = resp.get("paging", {}).get("cursors", {}).get("after")
            if not after:
                break
