# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from json import JSONEncoder
from typing import Any, Dict, List, Literal, Optional, Union

import aiohttp

from pythreads.credentials import Credentials
from pythreads.threads import Threads, ThreadsAccessTokenExpired

FIELD__AGE = "age"
FIELD__BREAKDOWN = "breakdown"
FIELD__CHILDREN = "children"
FIELD__CITY = "city"
FIELD__COUNTRY = "country"
FIELD__FOLLOWER_DEMOGRAPHICS = "follower_demographics"
FIELD__ERROR_MESSAGE = "error_message"
FIELD__FOLLOWERS_COUNT = "followers_count"
FIELD__GENDER = "gender"
FIELD__HIDE_STATUS = "hide_status"
FIELD__ID = "id"
FIELD__IS_QUOTE_POST = "is_quote_post"
FIELD__IS_REPLY = "is_reply"
FIELD__LIKES = "likes"
FIELD__MEDIA_PRODUCT_TYPE = "media_product_type"
FIELD__MEDIA_TYPE = "media_type"
FIELD__MEDIA_URL = "media_url"
FIELD__OWNER = "owner"
FIELD__PERMALINK = "permalink"
FIELD__QUOTES = "quotes"
FIELD__REPLIES = "replies"
FIELD__REPLY_AUDIENCE = "reply_audience"
FIELD__REPOSTS = "reposts"
FIELD__SHORTCODE = "shortcode"
FIELD__STATUS = "status"
FIELD__TEXT = "text"
FIELD__THREADS_BIOGRAPHY = "threads_biography"
FIELD__THREADS_PROFILE_PICTURE_URL = "threads_profile_picture_url"
FIELD__THUMBNAIL_URL = "thumbnail_url"
FIELD__TIMESTAMP = "timestamp"
FIELD__USERNAME = "username"
FIELD__VIEWS = "views"

USER_METRIC_TYPES = set(
    [
        FIELD__VIEWS,
        FIELD__LIKES,
        FIELD__REPLIES,
        FIELD__REPOSTS,
        FIELD__QUOTES,
        FIELD__FOLLOWERS_COUNT,
        FIELD__FOLLOWER_DEMOGRAPHICS,
    ]
)

UserMetricType = Literal[
    "views",
    "likes",
    "replies",
    "reposts",
    "quotes",
    "followers_count",
    "follower_demographics",
]

FOLLOWER_DEMOGRAPHIC_TYPES = set(
    [
        FIELD__AGE,
        FIELD__CITY,
        FIELD__COUNTRY,
        FIELD__GENDER,
    ]
)

FollowerDemographicType = Literal["age", "city", "country", "gender"]

MEDIA_TYPE__CAROUSEL = "CAROUSEL"
MEDIA_TYPE__IMAGE = "IMAGE"
MEDIA_TYPE__TEXT = "TEXT"
MEDIA_TYPE__VIDEO = "VIDEO"

PARAMS__ACCESS_TOKEN = "access_token"
PARAMS__AFTER = "after"
PARAMS__BEFORE = "before"
PARAMS__CHILDREN = "children"
PARAMS__CLIENT_ID = "client_id"
PARAMS__CONFIG = "config"
PARAMS__FIELDS = "fields"
PARAMS__HIDE = "hide"
PARAMS__IMAGE_URL = "image_url"
PARAMS__IS_CAROUSEL_ITEM = "is_carousel_item"
PARAMS__LIMIT = "limit"
PARAMS__MEDIA_TYPE = "media_type"
PARAMS__METRIC = "metric"
PARAMS__QUOTA_USAGE = "quota_usage"
PARAMS__REPLY_CONFIG = "reply_config"
PARAMS__REPLY_CONTROL = "reply_control"
PARAMS__REPLY_QUOTA_USAGE = "reply_quota_usage"
PARAMS__REPLY_TO_ID = "reply_to_id"
PARAMS__RESPONSE_TYPE = "response_type"
PARAMS__RETURN_URL = "return_url"
PARAMS__SCOPE = "scope"
PARAMS__SINCE = "since"
PARAMS__TEXT = "text"
PARAMS__UNTIL = "until"
PARAMS__USER_ID = "user_id"
PARAMS__VIDEO_URL = "video_url"


class ThreadsInvalidParameter(ValueError): ...


class ThreadsResponseError(Exception):
    def __init__(self, response: dict) -> None:
        super().__init__(JSONEncoder().encode(response))
        self.response = response


class MediaType(str, Enum):
    CAROUSEL = MEDIA_TYPE__CAROUSEL
    IMAGE = MEDIA_TYPE__IMAGE
    TEXT = MEDIA_TYPE__TEXT
    VIDEO = MEDIA_TYPE__VIDEO


class ReplyControl(str, Enum):
    ACCOUNTS_YOU_FOLLOW = "accounts_you_follow"
    EVERYONE = "everyone"
    MENTIONED_ONLY = "mentioned_only"


@dataclass
class Media:
    type: MediaType
    url: str


class PublishingStatus(str, Enum):
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
    FINISHED = "FINISHED"
    IN_PROGRESS = "IN_PROGRESS"
    PUBLISHED = "PUBLISHED"


class PublishingError(str, Enum):
    FAILED_DOWNLOADING_VIDEO = "FAILED_DOWNLOADING_VIDEO"
    FAILED_PROCESSING_AUDIO = "FAILED_PROCESSING_AUDIO"
    FAILED_PROCESSING_VIDEO = "FAILED_PROCESSING_VIDEO"
    INVALID_ASPEC_RATIO = "INVALID_ASPEC_RATIO"
    INVALID_BIT_RATE = "INVALID_BIT_RATE"
    INVALID_DURATION = "INVALID_DURATION"
    INVALID_FRAME_RATE = "INVALID_FRAME_RATE"
    INVALID_AUDIO_CHANNELS = "INVALID_AUDIO_CHANNELS"
    INVALID_AUDIO_CHANNEL_LAYOUT = "INVALID_AUDIO_CHANNEL_LAYOUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ContainerStatus:
    id: str
    status: PublishingStatus
    error: Optional[PublishingError] = None


class API:
    def __init__(
        self, credentials: Credentials, session: Optional[aiohttp.ClientSession] = None
    ) -> None:
        self.credentials = credentials
        self.external_session = session
        self._session = session

    @property
    def session(self) -> Optional[aiohttp.ClientSession]:
        return self._session

    @session.setter
    def session(self, value: aiohttp.ClientSession):
        self._session = value

    async def __aenter__(self) -> "API":
        if not self.external_session:
            self.session = aiohttp.ClientSession()
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

    async def _get(self, url: str) -> Any:
        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")

        async with self.session.get(url) as response:
            return await response.json()

    async def _post(self, url: str) -> Any:
        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")

        async with self.session.post(url) as response:
            return await response.json()

    async def account(self, user_id: str = "me") -> Any:
        """Retrieve a Threads User's Profile Information

        https://developers.facebook.com/docs/threads/threads-profiles

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing

        """
        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            user_id,
            {
                PARAMS__FIELDS: ",".join(
                    [
                        FIELD__THREADS_BIOGRAPHY,
                        FIELD__THREADS_PROFILE_PICTURE_URL,
                        FIELD__USERNAME,
                    ]
                )
            },
            access_token,
        )

        return await self._get(url)

    async def user_insights(
        self,
        metrics: Union[UserMetricType, List[UserMetricType]],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        breakdown: Optional[FollowerDemographicType] = None,
    ) -> Any:
        """Retrieve the available user insights metrics

        https://developers.facebook.com/docs/threads/insights#user-insights

        Args:
            metrics: The metric or metrics you want to retrieve (see linked official docs)
            since: [optional] The starting datetime of the time window you are requesting
            until: [optional] The ending datetime of the time window you are requesting
            breakdown: [optional] Required when requesting follower_demographic metrics

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsInvalidParameter: If you request a non-existent `metric` or
                fail to provide `breakdown` when required
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        # Ensure metrics is a list
        if isinstance(metrics, str):
            metrics = [metrics]

        requested_metrics = set(metrics)

        # Check that all the metrics are valid metric types
        invalid_metrics = requested_metrics.difference(USER_METRIC_TYPES)
        if len(invalid_metrics) > 0:
            raise ThreadsInvalidParameter(
                f"Invalid metrics provided: {', '.join(invalid_metrics)}"
            )

        # If "follower_demographics" is requested, then the "breakdown"
        # parameter is required: https://developers.facebook.com/docs/threads/insights#user-metrics
        if (
            # Requesting the follower_demographics metric
            FIELD__FOLLOWER_DEMOGRAPHICS in requested_metrics
            # and did not provide the required breakdown parameter
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

        url = Threads.build_graph_api_url(
            f"{user_id}/threads_insights", params, access_token
        )

        return await self._get(url)

    async def publishing_limit(self) -> Any:
        """The user's current Threads API usage total

        https://developers.facebook.com/docs/threads/troubleshooting#retrieve-publishing-quota-limit

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        user_id = self.credentials.user_id

        url = Threads.build_graph_api_url(
            f"{user_id}/threads_publishing_limit",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        PARAMS__CONFIG,
                        PARAMS__QUOTA_USAGE,
                        PARAMS__REPLY_CONFIG,
                        PARAMS__REPLY_QUOTA_USAGE,
                    ]
                )
            },
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
        """Creates a media container.

        While `text` and `media` are both optional, you must provide at least
        one or the other.

        Args:
            text: [optional] The thread's text
            media: [optional] The `Media` object
            reply_control: [optional] The `ReplyControl` policy to apply to the
                thread. Defaults to ReplyControl.EVERYONE.
            reply_to_id: [optional] The id of an existing thread to make this
                thread in reply to.
            is_carousel_item: A boolean indicating whether this is a media
                container that will be added to a carousel container

        Returns:
            The id of the published container

            https://developers.facebook.com/docs/threads/posts#step-2--publish-a-threads-media-container

            https://developers.facebook.com/docs/threads/posts#step-3--publish-the-carousel-container

        Raises:
            OAuth2Error: If there was an issue with the OAuth2 authentication
            ThreadsAccessTokenExpired: If the user's token has expired
            ThreadsAuthenticationError: If we receive an unexpected OAuth-related response from Threads
            ThreadsResponseError: If we receive an unexpected response from Threads
            RuntimeError: If the session is missing
        """

        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")

        access_token = self._access_token()

        # Construct parameters
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

        # Set media_type-specific parameters
        if media and media.type == MediaType.VIDEO:
            params[PARAMS__MEDIA_TYPE] = media.type.value
            params[PARAMS__VIDEO_URL] = media and media.url
        elif media and media.type == MediaType.IMAGE:
            params[PARAMS__MEDIA_TYPE] = media.type.value
            params[PARAMS__IMAGE_URL] = media and media.url

        # Construct URL
        user_id = self.credentials.user_id
        url = Threads.build_graph_api_url(f"{user_id}/threads", params, access_token)

        # Make the request and return the result
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
        """Creates a carousel container.

        Args:
            containers: A list of previously-created media containers that are
                to make up the carousel. You may provide between 2-10 media containers.
            text: [optional] The thread's text
            reply_control: [optional] The `ReplyControl` policy to apply to the
                thread. Defaults to "everyone".
            reply_to_id: [optional] The id of an existing thread to make this
                thread in reply to.

        Returns:
            The id of the published container
            https://developers.facebook.com/docs/threads/posts#step-2--publish-a-threads-media-container
            https://developers.facebook.com/docs/threads/posts#step-3--publish-the-carousel-container

        Raises:
            OAuth2Error: If there was an issue with the OAuth2 authentication
            ThreadsAccessTokenExpired: If the user's token has expired
            ThreadsAuthenticationError: If we receive an unexpected OAuth-related response from Threads
            ThreadsResponseError: If we receive an unexpected response from Threads
            ThreadsInvalidParameter: If you provide anything but 2-10 containers that are all in a state of "FINISHED".
            RuntimeError: If the session is missing
        """

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

        # Construct parameters
        params: Dict[str, Union[str, bool, List[str], None]] = {
            PARAMS__MEDIA_TYPE: MediaType.CAROUSEL.value,
            PARAMS__CHILDREN: children,
            PARAMS__REPLY_CONTROL: reply_control.value,
        }

        if text:
            params[PARAMS__TEXT] = text

        if reply_to_id:
            params[PARAMS__REPLY_TO_ID] = reply_to_id

        # Construct URL
        user_id = self.credentials.user_id
        url = Threads.build_graph_api_url(f"{user_id}/threads", params, access_token)

        # Make the request and return the result
        async with self.session.post(url) as resp:
            response = await resp.json()
            if "id" not in response:
                raise ThreadsResponseError(response)
            return response["id"]

    async def container_status(self, media_id: str) -> ContainerStatus:
        """Gets the container's publishing status

        https://developers.facebook.com/docs/threads/troubleshooting#publishing-does-not-return-a-media-id

        Args:
            media_id: The id of the container you want to know the status of

        Returns:
            A `ContainerStatus` object

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """
        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            f"{media_id}",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        FIELD__ID,
                        FIELD__STATUS,
                        FIELD__ERROR_MESSAGE,
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
        """Publish a container that has already been created.

        Args:
            container_id: The id of the container to publish. ids are returned
                from `create_container` and `create_carousel_container`

        Returns:
            The id of the published container

            https://developers.facebook.com/docs/threads/posts#step-2--publish-a-threads-media-container

            https://developers.facebook.com/docs/threads/posts#step-3--publish-the-carousel-container

        Raises:
            OAuth2Error: If there was an issue with the OAuth2 authentication
            ThreadsAccessTokenExpired: If the user's token has expired
            ThreadsAuthenticationError: If we receive an unexpected OAuth-related response from Threads
            ThreadsResponseError: If we receive an unexpected response from Threads
            RuntimeError: If the session is missing
        """

        if self.session is None:
            raise RuntimeError("an API instance must have a session to handle requests")

        access_token = self._access_token()

        user_id = self.credentials.user_id
        url = Threads.build_graph_api_url(
            f"{user_id}/threads_publish",
            {"creation_id": container_id},
            access_token,
        )
        async with self.session.post(url) as resp:
            response = await resp.json()
            if "id" not in response:
                raise ThreadsResponseError(response)
            return response["id"]

    async def container(self, container_id: str):
        """Retrieve an individual Threads media object (aka container)

        https://developers.facebook.com/docs/threads/threads-media#retrieve-a-single-threads-media-object

        Args:
            container_id: The id of the container you want to retrieve

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            f"{container_id}",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        FIELD__CHILDREN,
                        FIELD__ID,
                        FIELD__IS_QUOTE_POST,
                        FIELD__MEDIA_PRODUCT_TYPE,
                        FIELD__MEDIA_TYPE,
                        FIELD__MEDIA_URL,
                        FIELD__OWNER,
                        FIELD__PERMALINK,
                        FIELD__SHORTCODE,
                        FIELD__TEXT,
                        FIELD__THUMBNAIL_URL,
                        FIELD__TIMESTAMP,
                        FIELD__USERNAME,
                    ]
                )
            },
            access_token,
        )

        return await self._get(url)

    async def thread(self, thread_id: str):
        """Retrieve an individual thread

        https://developers.facebook.com/docs/threads/threads-media#retrieve-a-single-threads-media-object

        Args:
            thread_id: The id of the thread you want to retrieve

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

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
        """A paginated list of all threads created by the user

        Returns a paginated list of threads made by the user, including reposts.
        The number of threads returned is controlled by `limit`. The window of
        threads being queried is controlled by `since` and `until`. To
        paginate through that window, you use the `before` and `after` cursors
        returned in the response to request the next page. The `after` value
        that is returned in the response can be supplied to the `after` argument
        and it will retrieve the next page in the paginated list. The reverse
        direction is true for the `before value`.

        https://developers.facebook.com/docs/threads/threads-media#retrieve-a-list-of-all-a-user-s-threads


        Args:
            user_id: [optional] Which user ID to retrieve threads from.
            since: [optional] The starting `date` of the time window you are requesting
            until: [optional] The ending `date` of the time window you are requesting
            limit: [optional] The maximum number of threads to return. Defaults to 25.
            before: [optional] A before cursor for pagination that was returned from a previous request
            after: [optional] An after cursor for pagination that was returned from a previous request

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        if not user_id:
            user_id = self.credentials.user_id

        params = {
            PARAMS__FIELDS: ",".join(
                [
                    FIELD__CHILDREN,
                    FIELD__ID,
                    FIELD__IS_QUOTE_POST,
                    FIELD__MEDIA_PRODUCT_TYPE,
                    FIELD__MEDIA_TYPE,
                    FIELD__MEDIA_URL,
                    FIELD__OWNER,
                    FIELD__PERMALINK,
                    FIELD__SHORTCODE,
                    FIELD__TEXT,
                    FIELD__THUMBNAIL_URL,
                    FIELD__TIMESTAMP,
                    FIELD__USERNAME,
                ]
            )
        }

        # Handling string is legacy. Need to deprecate and remove.
        if since:
            if isinstance(since, date):
                since = since.isoformat()
            params[PARAMS__SINCE] = since

        # Handling string is legacy. Need to deprecate and remove.
        if until:
            if isinstance(until, date):
                until = until.isoformat()
            params[PARAMS__UNTIL] = until

        if limit:
            params[PARAMS__LIMIT] = f"{limit}"

        if before:
            params[PARAMS__BEFORE] = before

        if after:
            params[PARAMS__AFTER] = after

        url = Threads.build_graph_api_url(f"{user_id}/threads", params, access_token)
        return await self._get(url)

    async def replies(
        self,
        thread_id: str = "me",
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        """Returns the immediate replies of the requested `thread_id`

        https://developers.facebook.com/docs/threads/reply-management#replies

        Args:
            thread_id: The id of the thread or user whose immediate replies you want to retrieve.
                       Can also be "me" to retrieve all your replies.
            limit: [optional] The maximum number of threads to return. Defaults to 25.
            before: [optional] A before cursor for pagination that was returned from a previous request.
            after: [optional] An after cursor for pagination that was returned from a previous request.

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        params = {
            PARAMS__FIELDS: ",".join(
                [
                    FIELD__CHILDREN,
                    FIELD__ID,
                    FIELD__IS_QUOTE_POST,
                    FIELD__MEDIA_PRODUCT_TYPE,
                    FIELD__MEDIA_TYPE,
                    FIELD__MEDIA_URL,
                    FIELD__OWNER,
                    FIELD__PERMALINK,
                    FIELD__SHORTCODE,
                    FIELD__TEXT,
                    FIELD__THUMBNAIL_URL,
                    FIELD__TIMESTAMP,
                    FIELD__USERNAME,
                ]
            )
        }
        if limit:
            params[PARAMS__LIMIT] = f"{limit}"

        if before:
            params[PARAMS__BEFORE] = before

        if after:
            params[PARAMS__AFTER] = after

        url = Threads.build_graph_api_url(
            f"{thread_id}/replies",
            params,
            access_token,
        )

        return await self._get(url)

    async def conversation(
        self,
        thread_id: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        """Returns a paginated and flattened list of all top-level and nested replies of the requested `thread_id`

        Applicable to specific use cases that do not focus on the knowledge of
        the depthness of the replies. This endpoint is only intended to be used
        on the root-level threads with replies. To paginate through the replies,
        you use the `before` and `after` cursors returned in the response to
        request the next page. The `after` value that is returned in the
        response can be supplied to the `after` argument and it will retrieve
        the next page in the paginated list. The reverse direction is true
        for the `before value`.

        https://developers.facebook.com/docs/threads/reply-management#conversations

        Args:
            thread_id: The id of the thread whose replies you want to retrieve
            before: [optional] A before cursor for pagination that was returned from a previous request
            after: [optional] An after cursor for pagination that was returned from a previous request

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        params = {
            PARAMS__FIELDS: ",".join(
                [
                    FIELD__CHILDREN,
                    FIELD__ID,
                    FIELD__IS_QUOTE_POST,
                    FIELD__MEDIA_PRODUCT_TYPE,
                    FIELD__MEDIA_TYPE,
                    FIELD__MEDIA_URL,
                    FIELD__OWNER,
                    FIELD__PERMALINK,
                    FIELD__SHORTCODE,
                    FIELD__TEXT,
                    FIELD__THUMBNAIL_URL,
                    FIELD__TIMESTAMP,
                    FIELD__USERNAME,
                ]
            )
        }

        if before:
            params[PARAMS__BEFORE] = before

        if after:
            params[PARAMS__AFTER] = after

        url = Threads.build_graph_api_url(
            f"{thread_id}/conversation", params, access_token
        )

        return await self._get(url)

    async def manage_reply(self, reply_id: str, hide: bool):
        """Hide/unhide any top-level replies.

        This will automatically hide/unhide all the nested replies. Note: Replies
        nested deeper than the top-level reply cannot be targeted in isolation
        to be hidden/unhidden.

        https://developers.facebook.com/docs/threads/reply-management#hide-replies

        Args:
            reply_id: The id of the reply whose visibility you want to change
            hide: Whether to hide the reply or not

        Returns:
            The JSON response as a dict

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()

        params = {PARAMS__HIDE: hide}

        url = Threads.build_graph_api_url(
            f"{reply_id}/manage_reply", params, access_token
        )

        return await self._post(url)

    async def insights(
        self,
        thread_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ):
        """Retrieve the available insights metrics

        Returned metrics do not capture nested replies' metrics.

        https://developers.facebook.com/docs/threads/insights#media-insights

        Args:
            thread_id: The thread media id whose metrics you're requesting
            since: [optional] The starting datetime of the time window you are requesting
            until: [optional] The ending datetime of the time window you are requesting

        Returns:
            The JSON response as a dict. Requests all available metrics.

        Raises:
            ThreadsAccessTokenExpired: If the user's token has expired
            RuntimeError: If the session is missing
        """

        access_token = self._access_token()
        params = {
            PARAMS__METRIC: ",".join(
                [
                    FIELD__LIKES,
                    FIELD__QUOTES,
                    FIELD__REPLIES,
                    FIELD__REPOSTS,
                    FIELD__VIEWS,
                ]
            )
        }

        if since:
            params["since"] = int(since.timestamp())

        if until:
            params["until"] = int(until.timestamp())

        url = Threads.build_graph_api_url(
            f"{thread_id}/insights",
            params,
            access_token,
        )

        return await self._get(url)
