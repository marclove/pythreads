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
        access_token = self._access_token()
        url = self._build_url(user_id, {PARAMS__FIELDS: ",".join(fields)}, access_token)
        return await self._get(url)

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
        access_token = self._access_token()
        user_id = self.credentials.user_id
        url = self._build_url(
            f"{user_id}/threads_publishing_limit",
            {PARAMS__FIELDS: ",".join(fields)},
            access_token,
        )
        return await self._get(url)

    async def create_container(
        self,
        text: Optional[str] = None,
        media: Optional[Media] = None,
        reply_control: ReplyControl = ReplyControl.EVERYONE,
        reply_to_id: Optional[str] = None,
        is_carousel_item: bool = False,
    ) -> str:
        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")

        access_token = self._access_token()
        params: Dict[str, Union[str, bool, List[str], None]] = {
            PARAMS__REPLY_CONTROL: reply_control.value,
        }
        if text:
            params[PARAMS__TEXT] = text
            params[PARAMS__MEDIA_TYPE] = MediaType.TEXT.value
        if reply_to_id:
            params[PARAMS__REPLY_TO_ID] = reply_to_id
        if is_carousel_item:
            params[PARAMS__IS_CAROUSEL_ITEM] = is_carousel_item

        if media and media.type == MediaType.VIDEO:
            params[PARAMS__MEDIA_TYPE] = media.type.value
            params[PARAMS__VIDEO_URL] = media and media.url
        elif media and media.type == MediaType.IMAGE:
            params[PARAMS__MEDIA_TYPE] = media.type.value
            params[PARAMS__IMAGE_URL] = media and media.url

        user_id = self.credentials.user_id
        url = self._build_url(f"{user_id}/threads", params, access_token)
        async with self.session.post(url) as resp:
            response = await resp.json()
            if "id" not in response:
                raise ThreadsResponseError(response)
            return response["id"]

    async def create_carousel_container(
        self,
        containers: List[ContainerStatus],
        text: Optional[str] = None,
        reply_control: ReplyControl = ReplyControl.EVERYONE,
        reply_to_id: Optional[str] = None,
    ) -> str:
        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")
        access_token = self._access_token()

        num_media = len(containers)
        if num_media < 2 or num_media > 10:
            raise ThreadsInvalidParameter("a carousel post requires 2-10 media items")
        if any([item.status != PublishingStatus.FINISHED for item in containers]):
            raise ThreadsInvalidParameter(
                "all published_media must have a status of `FINISHED` before adding them to a carousel container"
            )
        child_ids = [item.id for item in containers]
        children = ",".join(child_ids)
        params: Dict[str, Union[str, bool, List[str], None]] = {
            PARAMS__MEDIA_TYPE: MediaType.CAROUSEL.value,
            PARAMS__CHILDREN: children,
            PARAMS__REPLY_CONTROL: reply_control.value,
        }
        if text:
            params[PARAMS__TEXT] = text
        if reply_to_id:
            params[PARAMS__REPLY_TO_ID] = reply_to_id
        user_id = self.credentials.user_id
        url = self._build_url(f"{user_id}/threads", params, access_token)
        async with self.session.post(url) as resp:
            response = await resp.json()
            if "id" not in response:
                raise ThreadsResponseError(response)
            return response["id"]

    async def container_status(self, media_id: str) -> ContainerStatus:
        access_token = self._access_token()
        url = self._build_url(
            f"{media_id}",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        Field.ID,
                        Field.STATUS,
                        Field.ERROR_MESSAGE,
                    ]
                )
            },
            access_token,
        )
        result: dict[Any, Any] = await self._get(url)
        status_str = result.get("status", PublishingStatus.ERROR)
        status = PublishingStatus[status_str]
        error = None
        error_str = result.get("error_message", None)
        if error_str and error_str != "":
            error = PublishingError[error_str]
        media = ContainerStatus(id=result["id"], status=status, error=error)
        return media

    async def publish_container(self, container_id: str) -> Dict[Any, Any]:
        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")
        access_token = self._access_token()
        user_id = self.credentials.user_id
        url = self._build_url(
            f"{user_id}/threads_publish", {"creation_id": container_id}, access_token
        )
        async with self.session.post(url) as resp:
            response = await resp.json()
            if "id" not in response:
                raise ThreadsResponseError(response)
            return response["id"]

    async def container(self, container_id: str):
        access_token = self._access_token()
        url = self._build_url(
            f"{container_id}",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        Field.CHILDREN,
                        Field.ID,
                        Field.IS_QUOTE_POST,
                        Field.MEDIA_PRODUCT_TYPE,
                        Field.MEDIA_TYPE,
                        Field.MEDIA_URL,
                        Field.OWNER,
                        Field.PERMALINK,
                        Field.SHORTCODE,
                        Field.TEXT,
                        Field.THUMBNAIL_URL,
                        Field.TIMESTAMP,
                        Field.USERNAME,
                    ]
                )
            },
            access_token,
        )
        return await self._get(url)

    async def thread(self, thread_id: str):
        return await self.container(container_id=thread_id)

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
        access_token = self._access_token()
        params: Dict[str, str] = {PARAMS__FIELDS: ",".join(fields)}
        if since:
            params[PARAMS__SINCE] = since if isinstance(since, str) else since.isoformat()
        if until:
            params[PARAMS__UNTIL] = until if isinstance(until, str) else until.isoformat()
        if limit:
            params[PARAMS__LIMIT] = str(limit)
        if before:
            params[PARAMS__BEFORE] = before
        if after:
            params[PARAMS__AFTER] = after
        user_id = user_id or self.credentials.user_id
        url = self._build_url(f"{user_id}/threads", params, access_token)
        return await self._get(url)

    async def replies(
        self, thread_id: str, fields: Iterable[str] = DEFAULT_REPLY_FIELDS
    ):
        access_token = self._access_token()
        url = self._build_url(
            f"{thread_id}/replies", {PARAMS__FIELDS: ",".join(fields)}, access_token
        )
        return await self._get(url)

    async def conversation(
        self,
        thread_id: str,
        fields: Iterable[str] = DEFAULT_CONVERSATION_FIELDS,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        access_token = self._access_token()
        params = {PARAMS__FIELDS: ",".join(fields)}
        if before:
            params[PARAMS__BEFORE] = before
        if after:
            params[PARAMS__AFTER] = after
        url = self._build_url(f"{thread_id}/conversation", params, access_token)
        return await self._get(url)

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
