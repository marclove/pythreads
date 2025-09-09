from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, Optional, Union

from pythreads.credentials import Credentials

from ..types import (
    ConversationResponse,
    DEFAULT_CONVERSATION_FIELDS,
    DEFAULT_REPLY_FIELDS,
    DEFAULT_THREAD_FIELDS,
    PARAMS__AFTER,
    PARAMS__BEFORE,
    PARAMS__FIELDS,
    PARAMS__LIMIT,
    PARAMS__SINCE,
    PARAMS__UNTIL,
    RepliesResponse,
    RequestOptions,
    ThreadsListResponse,
)
from ..utils import iso_date_or_str, PaginatedIterator
from ..transport import Transport


class ThreadsIterator(PaginatedIterator):
    """Specialized iterator for user threads with time-based filtering."""
    
    def __init__(self, transport, user_id: str, fields: Iterable[str], per_page: int = 25, page_limit: Optional[int] = None, **kwargs):
        endpoint = f"{user_id}/threads"
        super().__init__(transport, endpoint, fields, per_page, page_limit, **kwargs)
    
    def _build_params(self) -> Dict[str, str]:
        """Build parameters including time filters."""
        params = super()._build_params()
        
        # Handle time-based parameters specifically
        if 'since' in self.extra_params and self.extra_params['since']:
            params[PARAMS__SINCE] = iso_date_or_str(self.extra_params['since'])
        if 'until' in self.extra_params and self.extra_params['until']:
            params[PARAMS__UNTIL] = iso_date_or_str(self.extra_params['until'])
        
        return params


class RepliesIterator(PaginatedIterator):
    """Specialized iterator for thread replies."""
    
    def __init__(self, transport, thread_id: str, fields: Iterable[str], per_page: int = 25, page_limit: Optional[int] = None):
        endpoint = f"{thread_id}/replies"
        super().__init__(transport, endpoint, fields, per_page, page_limit)


class ConversationIterator(PaginatedIterator):
    """Specialized iterator for thread conversations."""
    
    def __init__(self, transport, thread_id: str, fields: Iterable[str], per_page: int = 25, page_limit: Optional[int] = None):
        endpoint = f"{thread_id}/conversation"
        super().__init__(transport, endpoint, fields, per_page, page_limit)


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
        *, request_options: RequestOptions | None = None) -> ThreadsListResponse:
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
        return await self.transport.get(f"{uid}/threads", params, request_options)

    async def replies(self, thread_id: str, fields: Iterable[str] = DEFAULT_REPLY_FIELDS, *, request_options: RequestOptions | None = None) -> RepliesResponse:
        return await self.transport.get(
            f"{thread_id}/replies", {PARAMS__FIELDS: ",".join(fields)}, request_options
        )

    async def conversation(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_CONVERSATION_FIELDS,
        before: Optional[str] = None,
        after: Optional[str] = None,
        *, request_options: RequestOptions | None = None) -> ConversationResponse:
        params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields)}
        if before:
            params[PARAMS__BEFORE] = before
        if after:
            params[PARAMS__AFTER] = after
        return await self.transport.get(f"{thread_id}/conversation", params, request_options)

    # ---------------------- Iterators (convenience) ----------------------

    def threads_iter(
        self,
        user_id: str | None = None,
        fields: Iterable[str] = DEFAULT_THREAD_FIELDS,
        since: Optional[Union[date, str]] = None,
        until: Optional[Union[date, str]] = None,
        per_page: int = 25,
        page_limit: Optional[int] = None,
    ) -> ThreadsIterator:
        uid = user_id or self.credentials.user_id
        return ThreadsIterator(
            transport=self.transport,
            user_id=uid,
            fields=fields,
            per_page=per_page,
            page_limit=page_limit,
            since=since,
            until=until
        )

    def replies_iter(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_REPLY_FIELDS,
        per_page: int = 25,
        page_limit: Optional[int] = None,
    ) -> RepliesIterator:
        return RepliesIterator(
            transport=self.transport,
            thread_id=thread_id,
            fields=fields,
            per_page=per_page,
            page_limit=page_limit
        )

    def conversation_iter(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_CONVERSATION_FIELDS,
        per_page: int = 25,
        page_limit: Optional[int] = None,
    ) -> ConversationIterator:
        return ConversationIterator(
            transport=self.transport,
            thread_id=thread_id,
            fields=fields,
            per_page=per_page,
            page_limit=page_limit
        )
