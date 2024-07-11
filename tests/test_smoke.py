# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import os
import unittest
from datetime import datetime, timedelta, timezone

import pytest

from pythreads.api import API
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

    async def test_smoke(self):
        access_token = os.environ["THREADS_SMOKE_TEST_TOKEN"]
        user_id = os.environ["THREADS_SMOKE_TEST_USER_ID"]

        credentials = Credentials(
            user_id=user_id,
            scopes=Threads.ALL_SCOPES,
            short_lived=False,
            access_token=access_token,
            expiration=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        async with API(credentials) as api:
            response = await api.threads()
            threads = response["data"]

            assert len(threads) == 25
