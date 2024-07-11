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
    Attachment,
    MediaType,
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
    async def test_publish_text_only_thread(self, mock_build_graph_api_url, mock_post):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response = {"id": "1"}
        publish_response = {"id": "1"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
        ]

        actual = await self.api.publish("Some text")

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "TEXT",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [call("https://some-uri.com"), call("https://some-uri.com")]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_text_only_with_options_thread(
        self, mock_build_graph_api_url, mock_post
    ):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response = {"id": "1"}
        publish_response = {"id": "1"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
        ]

        actual = await self.api.publish(
            "Some text", reply_control=ReplyControl.MENTIONED_ONLY, reply_to_id="999"
        )

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "TEXT",
                        "is_carousel_item": False,
                        "reply_control": "mentioned_only",
                        "reply_to_id": "999",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [call("https://some-uri.com"), call("https://some-uri.com")]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_image_only_thread(self, mock_build_graph_api_url, mock_post):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response = {"id": "1"}
        publish_response = {"id": "1"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
        ]

        attachment = Attachment(MediaType.IMAGE, "https://some-image-uri.com")
        actual = await self.api.publish(attachments=[attachment])

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [call("https://some-uri.com"), call("https://some-uri.com")]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_video_only_thread(self, mock_build_graph_api_url, mock_post):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response = {"id": "1"}
        publish_response = {"id": "1"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
        ]

        attachment = Attachment(MediaType.VIDEO, "https://some-video-uri.com")
        actual = await self.api.publish(attachments=[attachment])

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "VIDEO",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                        "video_url": "https://some-video-uri.com",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [call("https://some-uri.com"), call("https://some-uri.com")]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_image_and_text_thread(
        self, mock_build_graph_api_url, mock_post
    ):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response = {"id": "1"}
        publish_response = {"id": "1"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
        ]

        attachment = Attachment(MediaType.IMAGE, "https://some-image-uri.com")
        actual = await self.api.publish(text="Some text", attachments=[attachment])

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "IMAGE",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [call("https://some-uri.com"), call("https://some-uri.com")]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_video_and_text_thread(
        self, mock_build_graph_api_url, mock_post
    ):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response = {"id": "1"}
        publish_response = {"id": "1"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
        ]

        attachment = Attachment(MediaType.VIDEO, "https://some-video-uri.com")
        actual = await self.api.publish(text="Some text", attachments=[attachment])

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "VIDEO",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                        "video_url": "https://some-video-uri.com",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "1"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [call("https://some-uri.com"), call("https://some-uri.com")]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_carousel_only_thread(
        self, mock_build_graph_api_url, mock_post
    ):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response_1 = {"id": "1"}
        upload_response_2 = {"id": "2"}
        upload_response_3 = {"id": "3"}
        upload_response_4 = {"id": "4"}

        publish_response = {"id": "4"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response_1)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=upload_response_2)

        mock_response_3 = MagicMock()
        mock_response_3.json = AsyncMock(return_value=upload_response_3)

        mock_response_4 = MagicMock()
        mock_response_4.json = AsyncMock(return_value=upload_response_4)

        mock_response_5 = MagicMock()
        mock_response_5.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_3)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_4)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_5)),
        ]

        attachment_1 = Attachment(MediaType.IMAGE, "https://some-image-uri.com/1")
        attachment_2 = Attachment(MediaType.VIDEO, "https://some-video-uri.com/1")
        attachment_3 = Attachment(MediaType.IMAGE, "https://some-image-uri.com/2")
        actual = await self.api.publish(
            attachments=[attachment_1, attachment_2, attachment_3]
        )

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com/1",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "VIDEO",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "video_url": "https://some-video-uri.com/1",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com/2",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "CAROUSEL",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                        "children": ["1", "2", "3"],
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "4"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
            ]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_carousel_and_text_thread(
        self, mock_build_graph_api_url, mock_post
    ):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response_1 = {"id": "1"}
        upload_response_2 = {"id": "2"}
        upload_response_3 = {"id": "3"}
        upload_response_4 = {"id": "4"}

        publish_response = {"id": "4"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response_1)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=upload_response_2)

        mock_response_3 = MagicMock()
        mock_response_3.json = AsyncMock(return_value=upload_response_3)

        mock_response_4 = MagicMock()
        mock_response_4.json = AsyncMock(return_value=upload_response_4)

        mock_response_5 = MagicMock()
        mock_response_5.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_3)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_4)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_5)),
        ]

        attachment_1 = Attachment(MediaType.IMAGE, "https://some-image-uri.com/1")
        attachment_2 = Attachment(MediaType.VIDEO, "https://some-video-uri.com/1")
        attachment_3 = Attachment(MediaType.IMAGE, "https://some-image-uri.com/2")
        actual = await self.api.publish(
            text="Some text", attachments=[attachment_1, attachment_2, attachment_3]
        )

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com/1",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "VIDEO",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "video_url": "https://some-video-uri.com/1",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com/2",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "CAROUSEL",
                        "is_carousel_item": False,
                        "reply_control": None,
                        "reply_to_id": None,
                        "children": ["1", "2", "3"],
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "4"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
            ]
        )

        self.assertEqual(actual, publish_response)

    @patch("aiohttp.ClientSession.post")
    @patch("pythreads.api.Threads.build_graph_api_url")
    async def test_publish_carousel_and_text_with_options_thread(
        self, mock_build_graph_api_url, mock_post
    ):
        mock_build_graph_api_url.return_value = "https://some-uri.com"

        upload_response_1 = {"id": "1"}
        upload_response_2 = {"id": "2"}
        upload_response_3 = {"id": "3"}
        upload_response_4 = {"id": "4"}

        publish_response = {"id": "4"}

        mock_response_1 = MagicMock()
        mock_response_1.json = AsyncMock(return_value=upload_response_1)

        mock_response_2 = MagicMock()
        mock_response_2.json = AsyncMock(return_value=upload_response_2)

        mock_response_3 = MagicMock()
        mock_response_3.json = AsyncMock(return_value=upload_response_3)

        mock_response_4 = MagicMock()
        mock_response_4.json = AsyncMock(return_value=upload_response_4)

        mock_response_5 = MagicMock()
        mock_response_5.json = AsyncMock(return_value=publish_response)

        mock_post.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_1)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_2)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_3)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_4)),
            MagicMock(__aenter__=AsyncMock(return_value=mock_response_5)),
        ]

        attachment_1 = Attachment(MediaType.IMAGE, "https://some-image-uri.com/1")
        attachment_2 = Attachment(MediaType.VIDEO, "https://some-video-uri.com/1")
        attachment_3 = Attachment(MediaType.IMAGE, "https://some-image-uri.com/2")
        actual = await self.api.publish(
            text="Some text",
            attachments=[attachment_1, attachment_2, attachment_3],
            reply_control=ReplyControl.ACCOUNTS_YOU_FOLLOW,
            reply_to_id="9999",
        )

        mock_build_graph_api_url.assert_has_calls(
            [
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com/1",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "VIDEO",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "video_url": "https://some-video-uri.com/1",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": None,
                        "media_type": "IMAGE",
                        "is_carousel_item": True,
                        "reply_control": None,
                        "reply_to_id": None,
                        "image_url": "https://some-image-uri.com/2",
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads",
                    {
                        "text": "Some text",
                        "media_type": "CAROUSEL",
                        "is_carousel_item": False,
                        "reply_control": "accounts_you_follow",
                        "reply_to_id": "9999",
                        "children": ["1", "2", "3"],
                    },
                    "someaccesstoken",
                ),
                call(
                    f"{self.credentials.user_id}/threads_publish",
                    {"creation_id": "4"},
                    "someaccesstoken",
                ),
            ]
        )

        mock_post.assert_has_calls(
            [
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
                call("https://some-uri.com"),
            ]
        )

        self.assertEqual(actual, publish_response)

    async def test_publish_with_no_text_or_media(self):
        with self.assertRaises(ValueError):
            await self.api.publish(attachments=[])

    async def test_publish_with_expired_credentials(self):
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.publish()
        with self.assertRaises(ThreadsAccessTokenExpired):
            await self.api_with_expired_credentials.publish()

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
