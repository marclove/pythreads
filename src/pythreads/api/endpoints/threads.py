from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, Optional, Union

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
            params[PARAMS__SINCE] = since if isinstance(since, str) else since.isoformat()
        if until:
            params[PARAMS__UNTIL] = until if isinstance(until, str) else until.isoformat()
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

