# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import unittest
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import aiohttp

from pythreads.api import (
    API,
    ContainerStatus,
    Media,
    MediaType,
    PublishingError,
    PublishingStatus,
    ReplyControl,
    ThreadsInvalidParameter,
)
from pythreads.credentials import Credentials
from pythreads.threads import ThreadsAccessTokenExpired


def mock_response(mock: Any, response: Any):
    _mock = MagicMock()
    _mock.json = AsyncMock(return_value=response)
    mock.return_value.__aenter__.return_value = _mock


class APITest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.time = datetime.now(timezone.utc)

        self.credentials = Credentials(
            user_id="someuserid",
            scopes=["some.scope", "another.scope"],
            short_lived=False,
            access_token="someaccesstoken",
            expiration=(self.time + timedelta(days=1)),
        )

        self.expired_credentials = Credentials(
            user_id="someuserid",
            scopes=["some.scope", "another.scope"],
            short_lived=False,
            access_token="someaccesstoken",
            expiration=(self.time - timedelta(days=1)),
        )

        self.session = aiohttp.ClientSession()
        self.api = API(self.credentials, session=self.session)

        self.expired_session = aiohttp.ClientSession()
        self.api_with_expired_credentials = API(
            self.expired_credentials, session=self.expired_session
        )

    async def asyncTearDown(self):
        await self.session.close()
        await self.expired_session.close()

    async def test_init_with_session(self):
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        async with API(credentials=self.credentials, session=mock_session) as api:
            await api.threads()
        self.assertEqual(api.session, mock_session)

        # If you pass a session in, you're responsible for closing it
        mock_session.close.assert_not_called()
        # Ensure that the passed in session is what's getting used to make API calls
        mock_session.get.assert_called_once_with(ANY)
        args, _ = mock_session.get.call_args
        self.assertRegex(args[0], r"^https://graph\.threads\.net/someuserid/threads.*")

    @patch("aiohttp.ClientSession.get")
    @patch("aiohttp.ClientSession.close")
    async def test_init_without_session(self, mock_session_close, mock_session_get):
        async with API(credentials=self.credentials) as api:
            await api.threads()

        # If we're creating a session, we're responsible for closing it.
        mock_session_close.assert_called_once()
        # Ensure that session we created is what's getting used to make API calls
        mock_session_get.assert_called_once_with(ANY)
        args, _ = mock_session_get.call_args
        self.assertRegex(args[0], r"^https://graph\.threads\.net/someuserid/threads.*")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_account(self, mock_build_graph_api_url, mock_get):
        expected = {"username": self.credentials.user_id}
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.account()

        mock_build_graph_api_url.assert_called_once_with(
            "me",
            {
                "fields": ",".join(
                    [
                        "threads_biography",
                        "threads_profile_picture_url",
                        "username",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_account_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.account()

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_user_insights_single_metric(
        self, mock_build_graph_api_url, mock_get
    ):
        expected = {
            "data": [
                {
                    "name": "likes",
                    "period": "day",
                    "title": "likes",
                    "description": "The number of likes on your posts.",
                    "total_value": {"value": 92},
                    "id": "95561/insights/likes/day",
                }
            ],
            "paging": {
                "previous": "https://graph.threads.net/v1.0/95561/threads_insights?access_token=sometoken&pretty=0&metric=likes&since=1720554865&until=1720641265",
                "next": "https://graph.threads.net/v1.0/95561/threads_insights?access_token=sometoken&pretty=0&metric=likes&since=1720727667&until=1720814067",
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.user_insights("likes")

        mock_build_graph_api_url.assert_called_once_with(
            f"{self.credentials.user_id}/threads_insights",
            {"metric": "likes"},
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_user_insights_multiple_metrics(
        self, mock_build_graph_api_url, mock_get
    ):
        expected = {
            "data": [
                {
                    "name": "views",
                    "period": "day",
                    "values": [
                        {"value": 130, "end_time": "2024-07-10T07:00:00+0000"},
                        {"value": 227, "end_time": "2024-07-11T07:00:00+0000"},
                    ],
                    "title": "views",
                    "description": "The number of times your profile was viewed.",
                    "id": "95561/insights/views/day",
                },
                {
                    "name": "likes",
                    "period": "day",
                    "title": "likes",
                    "description": "The number of likes on your posts.",
                    "total_value": {"value": 92},
                    "id": "95561/insights/likes/day",
                },
            ],
            "paging": {
                "previous": "https://graph.threads.net/v1.0/95561/threads_insights?access_token=sometoken&pretty=0&metric=views%2Clikes&since=1720554967&until=1720641367",
                "next": "https://graph.threads.net/v1.0/95561/threads_insights?access_token=sometoken&pretty=0&metric=views%2Clikes&since=1720727769&until=1720814169",
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        since = datetime.now(timezone.utc) - timedelta(days=1)
        until = datetime.now(timezone.utc)

        actual = await self.api.user_insights(["views", "likes"], since, until)

        mock_build_graph_api_url.assert_called_once_with(
            f"{self.credentials.user_id}/threads_insights",
            {
                "metric": ",".join(["views", "likes"]),
                "since": int(since.timestamp()),
                "until": int(until.timestamp()),
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_user_insights_requesting_follower_demographics(
        self, mock_build_graph_api_url, mock_get
    ):
        expected = {
            "data": [
                {
                    "name": "follower_demographics",
                    "period": "day",
                    "title": "follower_demographics",
                    "description": "The demographic characteristics of followers, including countries, cities and gender distribution.",
                    "total_value": {
                        "breakdowns": [
                            {
                                "dimension_keys": ["age"],
                                "results": [
                                    {"dimension_values": ["13-17"], "value": 20},
                                    {"dimension_values": ["18-24"], "value": 30},
                                    {"dimension_values": ["25-34"], "value": 40},
                                    {"dimension_values": ["35-44"], "value": 50},
                                    {"dimension_values": ["45-54"], "value": 60},
                                    {"dimension_values": ["55-64"], "value": 70},
                                    {"dimension_values": ["65+"], "value": 80},
                                ],
                            }
                        ]
                    },
                    "id": "95561/insights/follower_demographics/day",
                }
            ],
            "paging": {
                "previous": "https://graph.threads.net/v1.0/95561/threads_insights?access_token=sometoken&pretty=0&breakdown=age&metric=follower_demographics&since=1720555091&until=1720641491",
                "next": "https://graph.threads.net/v1.0/95561/threads_insights?access_token=sometoken&pretty=0&breakdown=age&metric=follower_demographics&since=1720727893&until=1720814293",
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.user_insights("follower_demographics", breakdown="age")

        mock_build_graph_api_url.assert_called_once_with(
            f"{self.credentials.user_id}/threads_insights",
            {
                "metric": "follower_demographics",
                "breakdown": "age",
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_user_insights_follower_demographics_requires_breakdown(self):
        with self.assertRaises(ThreadsInvalidParameter):
            await self.api.user_insights("follower_demographics")

    async def test_user_insights_invalid_metric(self):
        with self.assertRaises(ThreadsInvalidParameter):
            await self.api.user_insights(["invalid"])  # type: ignore

    async def test_user_insights_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.user_insights("views")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publishing_limit(self, mock_build_graph_api_url, mock_get):
        expected = {
            "data": [
                {
                    "config": {"quota_total": 250, "quota_duration": 86400},
                    "quota_usage": 0,
                    "reply_config": {"quota_total": 1000, "quota_duration": 86400},
                    "reply_quota_usage": 0,
                }
            ]
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.publishing_limit()

        mock_build_graph_api_url.assert_called_once_with(
            f"{self.credentials.user_id}/threads_publishing_limit",
            {
                "fields": ",".join(
                    [
                        "config",
                        "quota_usage",
                        "reply_config",
                        "reply_quota_usage",
                    ]
                ),
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_publishing_limit_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.publishing_limit()

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_text_only_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        upload_response = {"id": "1"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=upload_response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        actual = await self.api.create_container("Some text")

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "TEXT",
                        "reply_control": "everyone",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "1")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_text_only_with_options_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        upload_response = {"id": "1"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=upload_response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        actual = await self.api.create_container(
            "Some text", reply_control=ReplyControl.MENTIONED_ONLY, reply_to_id="999"
        )

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "TEXT",
                        "reply_control": "mentioned_only",
                        "reply_to_id": "999",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "1")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_image_only_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        upload_response = {"id": "1"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=upload_response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        media = Media(MediaType.IMAGE, "https://some-image-uri.com")
        actual = await self.api.create_container(media=media)

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "media_type": "IMAGE",
                        "reply_control": "everyone",
                        "image_url": "https://some-image-uri.com",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "1")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_video_only_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        upload_response = {"id": "1"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=upload_response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        media = Media(MediaType.VIDEO, "https://some-image-uri.com")
        actual = await self.api.create_container(media=media)

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "media_type": "VIDEO",
                        "reply_control": "everyone",
                        "video_url": "https://some-image-uri.com",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "1")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_image_and_text_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        upload_response = {"id": "1"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=upload_response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        media = Media(MediaType.IMAGE, "https://some-image-uri.com")
        actual = await self.api.create_container(
            text="Some text", media=media, is_carousel_item=True
        )

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "IMAGE",
                        "reply_control": "everyone",
                        "image_url": "https://some-image-uri.com",
                        "is_carousel_item": True,
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "1")

    async def test_create_container_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            media = Media(MediaType.IMAGE, "https://some-image-uri.com")
            await self.api_with_expired_credentials.create_container(media=media)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_carousel_container(self, mock_build_graph_api_url, mock_post):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        response = {"id": "4"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        media_1 = ContainerStatus("1", PublishingStatus.FINISHED)
        media_2 = ContainerStatus("2", PublishingStatus.FINISHED)
        media_3 = ContainerStatus("3", PublishingStatus.FINISHED)
        actual = await self.api.create_carousel_container(
            containers=[media_1, media_2, media_3]
        )

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "media_type": "CAROUSEL",
                        "reply_control": "everyone",
                        "children": "1,2,3",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "4")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_carousel_and_text_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        response = {"id": "4"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        media_1 = ContainerStatus("1", PublishingStatus.FINISHED)
        media_2 = ContainerStatus("2", PublishingStatus.FINISHED)
        media_3 = ContainerStatus("3", PublishingStatus.FINISHED)
        actual = await self.api.create_carousel_container(
            text="Some text", containers=[media_1, media_2, media_3]
        )

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "CAROUSEL",
                        "reply_control": "everyone",
                        "children": "1,2,3",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "4")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_create_carousel_and_text_with_options_container(
        self, mock_build_graph_api_url, mock_post
    ):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        response = {"id": "4"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        media_1 = ContainerStatus("1", PublishingStatus.FINISHED)
        media_2 = ContainerStatus("2", PublishingStatus.FINISHED)
        media_3 = ContainerStatus("3", PublishingStatus.FINISHED)
        actual = await self.api.create_carousel_container(
            text="Some text",
            containers=[media_1, media_2, media_3],
            reply_control=ReplyControl.ACCOUNTS_YOU_FOLLOW,
            reply_to_id="9999",
        )

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "CAROUSEL",
                        "reply_control": "accounts_you_follow",
                        "reply_to_id": "9999",
                        "children": "1,2,3",
                    },
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "4")

    async def test_create_carousel_container_with_no_text_or_media(self):
        with self.assertRaises(ValueError):
            await self.api.create_carousel_container(containers=[])

    async def test_create_carousel_container_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            media_1 = ContainerStatus("1", PublishingStatus.FINISHED)
            media_2 = ContainerStatus("2", PublishingStatus.FINISHED)
            media_3 = ContainerStatus("3", PublishingStatus.FINISHED)
            await self.api_with_expired_credentials.create_carousel_container(
                containers=[media_1, media_2, media_3]
            )

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_container_status(self, mock_build_graph_api_url, mock_get):
        # Mock out responses
        expected = {
            "status": "FINISHED",
            "id": "17889615691921648",
        }
        expected_result = ContainerStatus(
            id="17889615691921648",
            status=PublishingStatus.FINISHED,
            error=None,
        )
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.container_status("17889615691921648")

        # Assertions
        mock_build_graph_api_url.assert_called_once_with(
            "17889615691921648",
            {
                "fields": ",".join(
                    [
                        "id",
                        "status",
                        "error_message",
                    ]
                ),
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected_result)

    async def test_container_status_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.container_status("someid")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_container_status_with_error(
        self, mock_build_graph_api_url, mock_get
    ):
        # Mock out responses
        expected = {
            "status": "ERROR",
            "id": "17889615691921648",
            "error_message": "FAILED_DOWNLOADING_VIDEO",
        }
        expected_result = ContainerStatus(
            id="17889615691921648",
            status=PublishingStatus.ERROR,
            error=PublishingError.FAILED_DOWNLOADING_VIDEO,
        )
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.container_status("17889615691921648")

        # Assertions
        mock_build_graph_api_url.assert_called_once_with(
            "17889615691921648",
            {
                "fields": ",".join(
                    [
                        "id",
                        "status",
                        "error_message",
                    ]
                ),
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected_result)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_container(self, mock_build_graph_api_url, mock_post):
        # Mock out responses
        mock_build_graph_api_url.return_value = "https://some-uri.com"
        response = {"id": "1"}
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=response)
        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response)),
        ]

        actual = await self.api.publish_container("1")

        # Assertions
        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls([call("https://some-uri.com")])

        self.assertEqual(actual, "1")

    async def test_publish_container_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.publish_container("1")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_container(self, mock_build_graph_api_url, mock_get):
        expected = {"id": "someid"}
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.container("someid")

        mock_build_graph_api_url.assert_called_once_with(
            "someid",
            {
                "fields": ",".join(
                    [
                        "children",
                        "id",
                        "is_quote_post",
                        "media_product_type",
                        "media_type",
                        "media_url",
                        "owner",
                        "permalink",
                        "shortcode",
                        "text",
                        "thumbnail_url",
                        "timestamp",
                        "username",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_container_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.container("someid")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_thread(self, mock_build_graph_api_url, mock_get):
        expected = {"id": "someid"}
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.thread("someid")

        mock_build_graph_api_url.assert_called_once_with(
            "someid",
            {
                "fields": ",".join(
                    [
                        "children",
                        "id",
                        "is_quote_post",
                        "media_product_type",
                        "media_type",
                        "media_url",
                        "owner",
                        "permalink",
                        "shortcode",
                        "text",
                        "thumbnail_url",
                        "timestamp",
                        "username",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_thread_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.thread("someid")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_threads(self, mock_build_graph_api_url, mock_get):
        expected = {
            "data": [{"id": "someid"}],
            "paging": {
                "cursors": {
                    "before": "TUJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWdzcFRIeJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWd",
                    "after": "lwMRYlFaR3lwMlEZAhcUtAzTW0ydUFMQzJ0MldSWExX0IUmZ1ad3lwMRlE3NwSWExX0IUmZ1ad3zZAWVJSWhmY",
                }
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.threads()

        mock_build_graph_api_url.assert_called_once_with(
            f"{self.credentials.user_id}/threads",
            {
                "fields": ",".join(
                    [
                        "children",
                        "id",
                        "is_quote_post",
                        "media_product_type",
                        "media_type",
                        "media_url",
                        "owner",
                        "permalink",
                        "shortcode",
                        "text",
                        "thumbnail_url",
                        "timestamp",
                        "username",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_threads_with_options(self, mock_build_graph_api_url, mock_get):
        expected = {
            "data": [{"id": "someid"}],
            "paging": {
                "cursors": {
                    "before": "TUJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWdzcFRIeJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWd",
                    "after": "lwMRYlFaR3lwMlEZAhcUtAzTW0ydUFMQzJ0MldSWExX0IUmZ1ad3lwMRlE3NwSWExX0IUmZ1ad3zZAWVJSWhmY",
                }
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.threads(
            since="2024-05-01", until="2024-06-01", limit=10
        )

        mock_build_graph_api_url.assert_called_once_with(
            f"{self.credentials.user_id}/threads",
            {
                "fields": ",".join(
                    [
                        "children",
                        "id",
                        "is_quote_post",
                        "media_product_type",
                        "media_type",
                        "media_url",
                        "owner",
                        "permalink",
                        "shortcode",
                        "text",
                        "thumbnail_url",
                        "timestamp",
                        "username",
                    ]
                ),
                "since": "2024-05-01",
                "until": "2024-06-01",
                "limit": "10",
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_threads_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.threads()

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_replies(self, mock_build_graph_api_url, mock_get):
        expected = {
            "data": [
                {
                    "id": "1234567890",
                    "text": "First Reply",
                    "timestamp": "2024-01-01T18:20:00+0000",
                    "media_product_type": "THREADS",
                    "media_type": "TEXT_POST",
                    "shortcode": "abcdefg",
                    "has_replies": True,
                    "root_post": {"id": "1234567890"},
                    "replied_to": {"id": "1234567890"},
                    "is_reply": True,
                    "hide_status": "NOT_HUSHED",
                },
                {
                    "id": "1234567890",
                    "text": "Second Reply",
                    "timestamp": "2024-01-01T18:20:00+0000",
                    "media_product_type": "THREADS",
                    "media_type": "TEXT_POST",
                    "shortcode": "abcdefg",
                    "has_replies": False,
                    "root_post": {"id": "1234567890"},
                    "replied_to": {"id": "1234567890"},
                    "is_reply": True,
                    "hide_status": "HIDDEN",
                },
            ],
            "paging": {
                "cursors": {
                    "before": "TUJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWdzcFRIeJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWd",
                    "after": "lwMRYlFaR3lwMlEZAhcUtAzTW0ydUFMQzJ0MldSWExX0IUmZ1ad3lwMRlE3NwSWExX0IUmZ1ad3zZAWVJSWhmY",
                }
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.replies("someid")

        mock_build_graph_api_url.assert_called_once_with(
            "someid/replies",
            {
                "fields": ",".join(
                    [
                        "children",
                        "id",
                        "is_quote_post",
                        "media_product_type",
                        "media_type",
                        "media_url",
                        "owner",
                        "permalink",
                        "shortcode",
                        "text",
                        "thumbnail_url",
                        "timestamp",
                        "username",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_replies_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.replies("someid")

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_conversation(self, mock_build_graph_api_url, mock_get):
        expected = {
            "data": [
                {
                    "id": "1234567890",
                    "text": "First Reply",
                    "timestamp": "2024-01-01T18:20:00+0000",
                    "media_product_type": "THREADS",
                    "media_type": "TEXT_POST",
                    "shortcode": "abcdefg",
                    "has_replies": True,
                    "root_post": {"id": "1234567890"},
                    "replied_to": {"id": "1234567890"},
                    "is_reply": True,
                    "hide_status": "NOT_HUSHED",
                },
                {
                    "id": "1234567890",
                    "text": "Second Reply",
                    "timestamp": "2024-01-01T18:20:00+0000",
                    "media_product_type": "THREADS",
                    "media_type": "TEXT_POST",
                    "shortcode": "abcdefg",
                    "has_replies": False,
                    "root_post": {"id": "1234567890"},
                    "replied_to": {"id": "1234567890"},
                    "is_reply": True,
                    "hide_status": "HIDDEN",
                },
                {
                    "id": "1234567890",
                    "text": "Nested Reply",
                    "timestamp": "2024-01-01T18:20:00+0000",
                    "media_product_type": "THREADS",
                    "media_type": "TEXT_POST",
                    "shortcode": "abcdefg",
                    "has_replies": False,
                    "root_post": {"id": "1234567890"},
                    "replied_to": {"id": "1234567890"},
                    "is_reply": True,
                    "hide_status": "NOT_HUSHED",
                },
            ],
            "paging": {
                "cursors": {
                    "before": "TUJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWdzcFRIeJzZAWVJSWhmYlFaR3lwMRldYNFJCSjVGb0ZAhWd",
                    "after": "lwMRYlFaR3lwMlEZAhcUtAzTW0ydUFMQzJ0MldSWExX0IUmZ1ad3lwMRlE3NwSWExX0IUmZ1ad3zZAWVJSWhmY",
                }
            },
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.conversation("someid")

        mock_build_graph_api_url.assert_called_once_with(
            "someid/conversation",
            {
                "fields": ",".join(
                    [
                        "children",
                        "id",
                        "is_quote_post",
                        "media_product_type",
                        "media_type",
                        "media_url",
                        "owner",
                        "permalink",
                        "shortcode",
                        "text",
                        "thumbnail_url",
                        "timestamp",
                        "username",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_conversation_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.conversation("someid")

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_manage_reply(self, mock_build_graph_api_url, mock_post):
        expected = {"success": True}
        mock_response(mock_post, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.manage_reply("someid", hide=True)

        mock_build_graph_api_url.assert_called_once_with(
            "someid/manage_reply",
            {"hide": True},
            "someaccesstoken",
        )

        mock_post.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_manage_reply_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.manage_reply("someid", hide=True)

    @patch("aiohttp.ClientSession.get")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_insights(self, mock_build_graph_api_url, mock_get):
        expected = {
            "data": [
                {
                    "name": "likes",
                    "period": "lifetime",
                    "values": [{"value": 100}],
                    "title": "Likes",
                    "description": "The number of likes on your post.",
                    "id": "someid/insights/likes/lifetime",
                },
                {
                    "name": "replies",
                    "period": "lifetime",
                    "values": [{"value": 10}],
                    "title": "Replies",
                    "description": "The number of replies on your post.",
                    "id": "someid/insights/replies/lifetime",
                },
            ]
        }
        mock_response(mock_get, expected)
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        actual = await self.api.insights("someid")

        mock_build_graph_api_url.assert_called_once_with(
            "someid/insights",
            {
                "fields": ",".join(
                    [
                        "likes",
                        "quotes",
                        "replies",
                        "reposts",
                        "views",
                    ]
                )
            },
            "someaccesstoken",
        )

        mock_get.assert_called_once_with("https://some-uri.com")

        self.assertEqual(actual, expected)

    async def test_insights_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.insights("someid")
