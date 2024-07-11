# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
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
class Attachment:
    type: MediaType
    url: str


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

    async def account(self) -> Any:
        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            "me",
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

    async def _create_container(
        self,
        session: aiohttp.ClientSession,
        attachment: Optional[Attachment] = None,
        text: Optional[str] = None,
        reply_control: Optional[ReplyControl] = None,
        reply_to_id: Optional[str] = None,
        children: Optional[List[str]] = None,
        is_carousel_item: bool = False,
    ) -> Dict[str, str]:
        """Creates a media container.

        Args:
            access_token: a valid access token
            attachment: [optional] an Attachment object, containing type and publicly-accessible URL for the media
            text: [optional] for carousel posts, text should be added to the parent container, not the child media containers
            reply_control: [optional] who should be allowed to reply to this container, defaults to everyone
            reply_to_id: [optional] the id of the post this container should be in reply to
            children: [optional] when creating a carousel media container, an array of the previously-created child media container ids
            is_carousel_item: True when creating media containers that will be a carousel's child
        """

        access_token = self._access_token()

        # Set the media type
        media_type = MediaType.TEXT
        if attachment:
            media_type = attachment.type
        if children and len(children) > 0:
            media_type = MediaType.CAROUSEL

        # There has to at least be a text value or an attachment
        if media_type is MediaType.TEXT and text is None:
            raise ValueError("you must provide either `text` or an `attachment`")

        # Construct parameters
        params: Dict[str, Union[str, bool, List[str], None]] = {
            PARAMS__TEXT: text,
            PARAMS__MEDIA_TYPE: media_type.value,
            PARAMS__IS_CAROUSEL_ITEM: is_carousel_item,
            PARAMS__REPLY_CONTROL: reply_control and reply_control.value,
            PARAMS__REPLY_TO_ID: reply_to_id,
        }

        # Set media_type-specific parameters
        if media_type == MediaType.CAROUSEL:
            params[PARAMS__CHILDREN] = children
        elif media_type == MediaType.VIDEO:
            params[PARAMS__VIDEO_URL] = attachment and attachment.url
        elif media_type == MediaType.IMAGE:
            params[PARAMS__IMAGE_URL] = attachment and attachment.url

        # Construct URL
        user_id = self.credentials.user_id
        url = Threads.build_graph_api_url(f"{user_id}/threads", params, access_token)

        # Make the request and return the result
        async with session.post(url) as resp:
            return await resp.json()

    async def _publish(
        self, session: aiohttp.ClientSession, container_id: str
    ) -> Dict[str, str]:
        access_token = self._access_token()

        user_id = self.credentials.user_id
        url = Threads.build_graph_api_url(
            f"{user_id}/threads_publish",
            {"creation_id": container_id},
            access_token,
        )
        async with session.post(url) as response:
            return await response.json()

    async def _post_non_carousel(
        self,
        attachment: Optional[Attachment] = None,
        text: Optional[str] = None,
        reply_control: Optional[ReplyControl] = None,
        reply_to_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Two steps:
        1. Create a single media container (with text and/or media)
        2. Publish the media container
        """

        # Create media container
        async with aiohttp.ClientSession() as session:
            container_response = await self._create_container(
                session=session,
                attachment=attachment,
                text=text,
                reply_control=reply_control,
                reply_to_id=reply_to_id,
            )

            if "id" not in container_response:
                raise RuntimeError(
                    "Expected 'id' key in JSON response from Threads API"
                )

            id = container_response["id"]

            return await self._publish(session, id)

    async def _post_carousel(
        self,
        attachments: List[Attachment],
        text: Optional[str] = None,
        reply_control: Optional[ReplyControl] = None,
        reply_to_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Three steps:
        1. Create media containers for each attachment.
        2. Create a carousel container with the containers from step 1 as children
        3. Publish the carousel container
        """

        if len(attachments) <= 1:
            raise ValueError(
                f"You are only posting {len(attachments)} attachments, so you do not need to post a carousel."
            )

        async with aiohttp.ClientSession() as session:
            # Create media containers for each attachment
            reqs = []
            for attachment in attachments:
                reqs.append(
                    asyncio.ensure_future(
                        self._create_container(
                            session=session,
                            attachment=attachment,
                            is_carousel_item=True,
                        )
                    )
                )
            responses = await asyncio.gather(*reqs)
            container_ids: list[str] = list(map(lambda resp: resp["id"], responses))

            # Create a parent container for all the media containers we just created
            parent_container_response = await self._create_container(
                session=session,
                text=text,
                reply_control=reply_control,
                reply_to_id=reply_to_id,
                children=container_ids,
            )

            if "id" not in parent_container_response:
                raise RuntimeError(
                    "Expected 'id' key in JSON response from Threads API"
                )

            id = parent_container_response["id"]

            return await self._publish(session, id)

    async def publish(
        self,
        text: Optional[str] = None,
        attachments: List[Attachment] = [],
        reply_control: Optional[ReplyControl] = None,
        reply_to_id: Optional[str] = None,
    ):
        """A unified interface for uploading and publishing threads of any kind.

        Lets you upload and publish:
        - A text only thread
        - An image thread, with or without text
        - A video thread, with or without text
        - A carousel thread of images and/or videos, with or without text

        You must provide at least text or an attachment.

        Args:
            text: [optional] The thread's text
            attachments: [optional] The `Attachment`(s) to include in the thread
            reply_control: [optional] The `ReplyControl` policy to apply to the thread. Defaults to "everyone".
            reply_to_id: [optional] The id of an existing thread to make this thread in reply to.

        Returns:
            The JSON response of the `threads_publish` endpoint, which is
            currently simply the published thread's ID: `{ "id": "1234567" }`
            https://developers.facebook.com/docs/threads/posts#step-2--publish-a-threads-media-container
            https://developers.facebook.com/docs/threads/posts#step-3--publish-the-carousel-container

        Raises:
            OAuth2Error: If there was an issue with the OAuth2 authentication
            ThreadsAccessTokenExpired: If the user's token has expired
            ThreadsAuthenticationError: If we receive an unexpected OAuth-related response from Threads
            ValueError: If you did not provide either `text` or at least one `attachment`
            RuntimeError: If we receive an unexpected upload-related response from Threads
        """
        attachments_count = 0
        if attachments:
            attachments_count = len(attachments)

        if attachments_count == 0:
            return await self._post_non_carousel(
                text=text,
                reply_control=reply_control,
                reply_to_id=reply_to_id,
            )
        elif attachments_count == 1:
            return await self._post_non_carousel(
                attachment=attachments[0],
                text=text,
                reply_control=reply_control,
                reply_to_id=reply_to_id,
            )
        else:
            return await self._post_carousel(
                attachments=attachments,
                text=text,
                reply_control=reply_control,
                reply_to_id=reply_to_id,
            )

    async def container(self, container_id: str):
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
        return await self.container(container_id=thread_id)

    async def threads(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        access_token = self._access_token()

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

        if since:
            params[PARAMS__SINCE] = since

        if until:
            params[PARAMS__UNTIL] = until

        if limit:
            params[PARAMS__LIMIT] = f"{limit}"

        url = Threads.build_graph_api_url(f"{user_id}/threads", params, access_token)
        return await self._get(url)

    async def replies(self, thread_id: str):
        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            f"{thread_id}/replies",
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

    async def conversation(self, thread_id: str):
        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            f"{thread_id}/conversation",
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

    async def manage_reply(self, reply_id: str, hide: bool):
        access_token = self._access_token()

        params = {PARAMS__HIDE: hide}

        url = Threads.build_graph_api_url(
            f"{reply_id}/manage_reply", params, access_token
        )

        return await self._post(url)

    async def insights(self, thread_id: str):
        access_token = self._access_token()

        url = Threads.build_graph_api_url(
            f"{thread_id}/insights",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        FIELD__LIKES,
                        FIELD__QUOTES,
                        FIELD__REPLIES,
                        FIELD__REPOSTS,
                        FIELD__VIEWS,
                    ]
                )
            },
            access_token,
        )

        return await self._get(url)
