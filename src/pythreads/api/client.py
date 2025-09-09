from __future__ import annotations

import asyncio
import logging
import random
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import aiohttp

from pythreads.credentials import Credentials
from pythreads.threads import Threads, ThreadsAccessTokenExpired

from .errors import ThreadsHTTPError, ThreadsInvalidParameter, ThreadsResponseError
from .types import (
    DEFAULT_ACCOUNT_FIELDS,
    DEFAULT_CONVERSATION_FIELDS,
    DEFAULT_METRIC_FIELDS,
    DEFAULT_PUBLISHING_LIMIT_FIELDS,
    DEFAULT_REPLY_FIELDS,
    DEFAULT_THREAD_FIELDS,
    ContainerStatus,
    Field,
    FollowerDemographicType,
    FOLLOWER_DEMOGRAPHIC_TYPES,
    Media,
    MediaType,
    PARAMS__AFTER,
    PARAMS__BEFORE,
    PARAMS__CHILDREN,
    PARAMS__FIELDS,
    PARAMS__HIDE,
    PARAMS__IMAGE_URL,
    PARAMS__IS_CAROUSEL_ITEM,
    PARAMS__LIMIT,
    PARAMS__MEDIA_TYPE,
    PARAMS__METRIC,
    PARAMS__REPLY_CONTROL,
    PARAMS__REPLY_TO_ID,
    PARAMS__SINCE,
    PARAMS__TEXT,
    PARAMS__UNTIL,
    PARAMS__VIDEO_URL,
    PublishingError,
    PublishingStatus,
    ReplyControl,
    USER_METRIC_TYPES,
)
from .transport import Transport
from .endpoints.accounts import AccountsService
from .endpoints.threads import ThreadsService
from .endpoints.media import MediaService

logger = logging.getLogger(__name__)


class API:
    """HTTP client for the Threads Graph API.

    Options
    - timeout: float seconds or aiohttp.ClientTimeout (default 30)
    - base_url: override base API URL (default Threads' base URL)
    - retries: number of retries for transient HTTP statuses (default 0)
    - backoff_base: initial backoff seconds for retries (default 0.5)
    - backoff_max: maximum backoff seconds (default 4.0)
    """
    def __init__(
        self,
        credentials: Credentials,
        session: Optional[aiohttp.ClientSession] = None,
        *,
        timeout: Optional[Union[float, aiohttp.ClientTimeout]] = 30,
        base_url: Optional[str] = None,
        retries: int = 0,
        backoff_base: float = 0.5,
        backoff_max: float = 4.0,
    ) -> None:
        self.credentials = credentials
        self.external_session = session
        self._session = session
        self.manage_session: bool = False
        self.timeout = timeout
        self.base_url = base_url
        self.retries = max(0, int(retries))
        self.backoff_base = float(backoff_base)
        self.backoff_max = float(backoff_max)
        self.transport: Transport | None = None
        self.accounts: AccountsService | None = None
        self.threads_service: ThreadsService | None = None
        self.media_service: MediaService | None = None
        # If a session is provided, wire transport and services immediately
        if self._session is not None:
            self.transport = Transport(
                session=self._session,
                credentials=self.credentials,
                timeout=self.timeout,
                base_url=self.base_url,
                retries=self.retries,
                backoff_base=self.backoff_base,
                backoff_max=self.backoff_max,
            )
            self.accounts = AccountsService(self.transport, self.credentials)
            self.threads_service = ThreadsService(self.transport, self.credentials)
            self.media_service = MediaService(self.transport, self.credentials)

    @property
    def session(self) -> Optional[aiohttp.ClientSession]:
        return self._session

    @session.setter
    def session(self, value: aiohttp.ClientSession):
        self._session = value

    async def __aenter__(self) -> "API":
        if not self.external_session:
            if isinstance(self.timeout, (int, float)) and self.timeout:
                timeout = aiohttp.ClientTimeout(total=float(self.timeout))
            elif isinstance(self.timeout, aiohttp.ClientTimeout):
                timeout = self.timeout
            else:
                timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.manage_session = True
        else:
            self.session = self.external_session
            self.manage_session = False
        # Wire transport and services
        sess = self.session
        assert sess is not None
        self.transport = Transport(
            session=sess,
            credentials=self.credentials,
            timeout=self.timeout,
            base_url=self.base_url,
            retries=self.retries,
            backoff_base=self.backoff_base,
            backoff_max=self.backoff_max,
        )
        self.accounts = AccountsService(self.transport, self.credentials)
        self.threads_service = ThreadsService(self.transport, self.credentials)
        self.media_service = MediaService(self.transport, self.credentials)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.manage_session and self.session:
            await self.session.close()

    def _access_token(self) -> str:
        if self.credentials.expired():
            raise ThreadsAccessTokenExpired()
        return self.credentials.access_token

    def _build_url(
        self, path: str, params: Optional[Dict[str, Any]], access_token: str
    ) -> str:
        # Keep legacy URL builder for now. New services use Transport._build_url.
        if self.base_url:
            return Threads.build_graph_api_url(path, params or {}, access_token, self.base_url)
        return Threads.build_graph_api_url(path, params or {}, access_token)

    async def _request(self, method: str, url: str) -> Any:
        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")
        http_method = getattr(self.session, method)
        attempts = self.retries + 1
        for i in range(1, attempts + 1):
            async with http_method(url) as response:
                status = getattr(response, "status", 200)
                if isinstance(status, int) and status >= 400:
                    # Retry only for transient or throttling statuses
                    should_retry = status == 429 or 500 <= status <= 599
                    if should_retry and i <= self.retries:
                        delay = min(self.backoff_base * (2 ** (i - 1)) + random.uniform(0, 0.1), self.backoff_max)
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

    async def _get(self, url: str) -> Any:
        return await self._request("get", url)

    async def _post(self, url: str) -> Any:
        return await self._request("post", url)

    async def account(
        self,
        user_id: str = "me",
        fields: Sequence[str] = DEFAULT_ACCOUNT_FIELDS,
    ) -> Any:
        assert self.accounts is not None
        return await self.accounts.account(user_id=user_id, fields=fields)

    async def user_insights(
        self,
        metrics: Union[str, List[str]],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        breakdown: Optional[FollowerDemographicType] = None,
    ) -> Any:
        access_token = self._access_token()

        if isinstance(metrics, str):
            metrics = [metrics]
        requested_metrics = set(metrics)
        invalid_metrics = requested_metrics.difference(USER_METRIC_TYPES)
        if len(invalid_metrics) > 0:
            raise ThreadsInvalidParameter(
                f"Invalid metrics provided: {', '.join(invalid_metrics)}"
            )
        if (
            Field.FOLLOWER_DEMOGRAPHICS in requested_metrics
            and breakdown not in FOLLOWER_DEMOGRAPHIC_TYPES
        ):
            raise ThreadsInvalidParameter(
                "follower_demographics metric requires a breakdown value"
            )

        params: Dict[str, str | float] = {PARAMS__METRIC: ",".join(metrics)}
        if since:
            params["since"] = int(since.timestamp())
        if until:
            params["until"] = int(until.timestamp())
        if breakdown:
            params["breakdown"] = breakdown

        user_id = self.credentials.user_id
        url = self._build_url(f"{user_id}/threads_insights", params, access_token)
        return await self._get(url)

    async def publishing_limit(
        self, fields: Sequence[str] = DEFAULT_PUBLISHING_LIMIT_FIELDS
    ) -> Any:
        assert self.accounts is not None
        return await self.accounts.publishing_limit(fields=fields)

    async def create_container(
        self,
        text: Optional[str] = None,
        media: Optional[Media] = None,
        reply_control: ReplyControl = ReplyControl.EVERYONE,
        reply_to_id: Optional[str] = None,
        is_carousel_item: bool = False,
    ) -> str:
        assert self.media_service is not None
        return await self.media_service.create_container(
            text=text,
            media=media,
            reply_control=reply_control,
            reply_to_id=reply_to_id,
            is_carousel_item=is_carousel_item,
        )

    async def create_carousel_container(
        self,
        containers: List[ContainerStatus],
        text: Optional[str] = None,
        reply_control: ReplyControl = ReplyControl.EVERYONE,
        reply_to_id: Optional[str] = None,
    ) -> str:
        assert self.media_service is not None
        return await self.media_service.create_carousel_container(
            containers=containers,
            text=text,
            reply_control=reply_control,
            reply_to_id=reply_to_id,
        )

    async def container_status(self, media_id: str) -> ContainerStatus:
        assert self.media_service is not None
        return await self.media_service.container_status(media_id)

    async def publish_container(self, container_id: str) -> str:
        assert self.media_service is not None
        return await self.media_service.publish_container(container_id)

    async def container(self, container_id: str):
        assert self.media_service is not None
        return await self.media_service.container(container_id)

    async def thread(self, thread_id: str):
        assert self.media_service is not None
        return await self.media_service.thread(thread_id)

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
        assert self.threads_service is not None
        return await self.threads_service.threads(
            user_id=user_id,
            fields=fields,
            since=since,
            until=until,
            limit=limit,
            before=before,
            after=after,
        )

    async def replies(
        self, thread_id: str, fields: Iterable[str] = DEFAULT_REPLY_FIELDS
    ):
        assert self.threads_service is not None
        return await self.threads_service.replies(thread_id, fields)

    async def conversation(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_CONVERSATION_FIELDS,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        assert self.threads_service is not None
        return await self.threads_service.conversation(
            thread_id, fields=fields, before=before, after=after
        )

    async def manage_reply(self, reply_id: str, hide: bool):
        access_token = self._access_token()
        params = {PARAMS__HIDE: hide}
        url = self._build_url(f"{reply_id}/manage_reply", params, access_token)
        return await self._post(url)

    async def insights(
        self,
        thread_id: str,
        metric: Sequence[str] = DEFAULT_METRIC_FIELDS,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ):
        access_token = self._access_token()
        params: Dict[str, str] = {PARAMS__FIELDS: ",".join(metric)}
        if since:
            params["since"] = str(int(since.timestamp()))
        if until:
            params["until"] = str(int(until.timestamp()))
        url = self._build_url(f"{thread_id}/insights", params, access_token)
        return await self._get(url)
