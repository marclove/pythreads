# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone

import pytest

from pythreads.api import API, Media, MediaType
from pythreads.credentials import Credentials
from pythreads.threads import Threads


@pytest.mark.smoke
class APITest(unittest.IsolatedAsyncioTestCase):
    # Running Smoke Tests
    #
    # To run smoke tests, you need to set both the THREADS_SMOKE_TEST_USER_ID
    # and THREADS_SMOKE_TEST_TOKEN environment variables.
    #
    # THREADS_SMOKE_TEST_USER_ID is a real Threads user id
    # THREADS_SMOKE_TEST_TOKEN is a valid OAuth2 authentication token for that same user
    #
    # To make it convenient to retrieve both, this library comes with a simple
    # server to generate a link and convert the redirect to a long-lived token.
    #
    # The callback that this server accepts must happen over an SSL connection,
    # so you will need to set up all the environment variables defined in the
    # .env.template file, including the local hostname information, app
    # credentials, and self-signed cert information.
    #
    # Once you've set up your app, cert, and set the environment variables, you
    # can run the test server:
    #
    # >>> python3 tests/server.py
    #
    # Click the link to authorize your application with your user account. It
    # will redirect back to the local server and display your user id and
    # oauth token. Add these in your environment variables and run the smoke
    # tests:
    #
    # >>> hatch run smoke-test:all
    #

    async def asyncSetUp(self):
        self.credentials = Credentials(
            user_id=os.environ["THREADS_SMOKE_TEST_USER_ID"],
            scopes=Threads.ALL_SCOPES,
            short_lived=False,
            access_token=os.environ["THREADS_SMOKE_TEST_TOKEN"],
            expiration=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def test_get_posts(self):
        async with API(self.credentials) as api:
            response = await api.threads()
            threads = response["data"]
            assert len(threads) == 25

    async def test_post_text(self):
        async with API(self.credentials) as api:
            id = await api.create_container("A text-only post")
            response = await api.publish_container(id)
            print(response)
            assert response is not None

    async def test_post_single_photo(self):
        async with API(self.credentials) as api:
            # Post with a one image
            an_image = Media(
                type=MediaType.IMAGE, url="https://marclove.s3.amazonaws.com/python.png"
            )
            image_id = await api.create_container(media=an_image)

            await asyncio.sleep(15)

            status = await api.container_status(image_id)
            print(status)

            response = await api.publish_container(image_id)
            print(response)
            assert response is not None

    async def test_post_carousel(self):
        async with API(self.credentials) as api:
            an_image = Media(
                type=MediaType.IMAGE, url="https://marclove.s3.amazonaws.com/python.png"
            )
            image_id = await api.create_container(media=an_image, is_carousel_item=True)

            a_video = Media(
                type=MediaType.VIDEO,
                url="https://marclove.s3.amazonaws.com/actually-you-didnt.mp4",
            )
            video_id = await api.create_container(media=a_video, is_carousel_item=True)

            await asyncio.sleep(30)

            status_1 = await api.container_status(image_id)
            status_2 = await api.container_status(video_id)

            print(status_1)
            print(status_2)

            carousel_id = await api.create_carousel_container(
                containers=[status_1, status_2], text="Here's a carousel"
            )

            await asyncio.sleep(15)

            carousel_status = await api.container_status(carousel_id)
            print(carousel_status)

            response = await api.publish_container(carousel_id)
            print(response)
            assert response is not None
