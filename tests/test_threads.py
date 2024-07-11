# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, MagicMock, patch

from pythreads.configuration import Configuration
from pythreads.credentials import Credentials
from pythreads.threads import Threads, ThreadsAccessTokenExpired


class ThreadsTest(unittest.TestCase):
    def setUp(self):
        self.configuration = Configuration(
            scopes=["some.scope", "another.scope"],
            app_id="someappid",
            api_secret="someapisecret",
            redirect_uri="https://some.secure.app.url/redirect",
        )

        self.time = datetime.now(timezone.utc) + timedelta(days=1)

        self.credentials = Credentials(
            user_id="someuserid",
            scopes=["some.scope", "another.scope"],
            short_lived=False,
            access_token="someaccesstoken",
            expiration=self.time,
        )

    def test_build_graph_api_url(self):
        without_params_or_access_token = Threads.build_graph_api_url(
            path="/some_path", params={}, base_url="https://threads.api"
        )
        self.assertEqual(
            without_params_or_access_token, "https://threads.api/some_path"
        )

        without_params = Threads.build_graph_api_url(
            path="/some_path",
            params={},
            access_token="some_access_token",
            base_url="https://threads.api",
        )
        self.assertEqual(
            without_params,
            "https://threads.api/some_path?access_token=some_access_token",
        )

        without_access_token = Threads.build_graph_api_url(
            path="/some_path",
            params={"some": "value", "another": "value"},
            base_url="https://threads.api",
        )
        self.assertEqual(
            without_access_token,
            "https://threads.api/some_path?some=value&another=value",
        )

        with_params_and_access_token = Threads.build_graph_api_url(
            path="/some_path",
            params={"some": "value", "another": "value"},
            access_token="some_access_token",
            base_url="https://threads.api",
        )
        self.assertEqual(
            with_params_and_access_token,
            "https://threads.api/some_path?some=value&another=value&access_token=some_access_token",
        )

    def test_load_configuration_with_scopes(self):
        config = Threads.load_configuration(
            scopes=["one", "two", "three"],
            app_id="app_id",
            api_secret="api_secret",
            redirect_uri="https://threads-meta.local",
        )
        self.assertEqual(config.scopes, ["one", "two", "three"])
        self.assertEqual(config.app_id, "app_id")
        self.assertEqual(config.api_secret, "api_secret")
        self.assertEqual(config.redirect_uri, "https://threads-meta.local")

    def test_load_configuration_without_scopes_defaults_to_all(self):
        config = Threads.load_configuration(
            app_id="app_id",
            api_secret="api_secret",
            redirect_uri="https://threads-meta.local",
        )
        self.assertEqual(
            config.scopes,
            [
                "threads_basic",
                "threads_content_publish",
                "threads_manage_insights",
                "threads_manage_replies",
                "threads_read_replies",
            ],
        )
        self.assertEqual(config.app_id, "app_id")
        self.assertEqual(config.api_secret, "api_secret")
        self.assertEqual(config.redirect_uri, "https://threads-meta.local")

    @patch("pythreads.threads.OAuth2Session")
    def test_threads_authorization_url(self, MockOAuth2Session):
        expected = ("https://auth.url", "state_value")
        mock_instance = MockOAuth2Session.return_value
        mock_instance.authorization_url.return_value = expected

        actual = Threads.authorization_url(config=self.configuration)

        MockOAuth2Session.assert_called_once_with(
            scope=",".join(self.configuration.scopes),
            client_id=self.configuration.app_id,
            redirect_uri=self.configuration.redirect_uri,
        )
        self.assertEqual(actual, expected)

    @patch("pythreads.threads.Threads.fetch_long_lived_token")
    @patch("pythreads.threads.Threads.fetch_user_id_and_token")
    def test_complete_authorization_with_long_lived_false(
        self, fetch_user_id_and_token, fetch_long_lived_token
    ):
        expected = self.credentials
        expected.short_lived = True

        # Expects that it calls fetch_user_id_and_token with the callback_url and configuration
        fetch_user_id_and_token.return_value = (
            "someuserid",
            "someaccesstoken",
            self.time,
        )

        actual = Threads.complete_authorization(
            callback_url="https://auth.url",
            state="somestatetoken",
            long_lived_token=False,
            config=self.configuration,
        )

        fetch_user_id_and_token.assert_called_once_with(
            request_url="https://auth.url",
            state="somestatetoken",
            config=self.configuration,
        )

        fetch_long_lived_token.assert_not_called()

        self.assertEqual(actual, expected)

    @patch("pythreads.threads.Threads.fetch_long_lived_token")
    @patch("pythreads.threads.Threads.fetch_user_id_and_token")
    def test_complete_authorization_with_long_lived_true(
        self, fetch_user_id_and_token, fetch_long_lived_token
    ):
        expected = self.credentials
        expected.short_lived = False

        # Expects that it calls fetch_user_id_and_token with the callback_url and configuration
        fetch_user_id_and_token.return_value = (
            "someuserid",
            "someaccesstoken",
            self.time,
        )

        fetch_long_lived_token.return_value = (
            "someaccesstoken",
            self.time,
        )

        actual = Threads.complete_authorization(
            callback_url="https://auth.url",
            state="somestatetoken",
            long_lived_token=True,
            config=self.configuration,
        )

        fetch_user_id_and_token.assert_called_once_with(
            request_url="https://auth.url",
            state="somestatetoken",
            config=self.configuration,
        )

        fetch_long_lived_token.assert_called_once_with(
            access_token="someaccesstoken",
            expiration=self.time,
            config=self.configuration,
        )

        self.assertEqual(actual, expected)

    @patch("pythreads.threads.datetime", wraps=datetime)
    @patch("pythreads.threads.Threads.build_graph_api_url")
    @patch("pythreads.threads.OAuth2Session")
    def test_fetch_user_id_and_token(
        self, MockOAuth2Session, build_graph_api_url, mock_datetime
    ):
        # Set expectations
        expected_uri = "https://some-uri.com"
        expected = ("someuserid", "someaccesstoken", self.time + timedelta(hours=1))

        # Mock collaborators
        mock_datetime.now.return_value = self.time
        mock_datetime.now.timezone = timezone.utc
        mock_oauth2_session_instance = MockOAuth2Session.return_value
        mock_oauth2_session_instance.fetch_token.return_value = {
            "user_id": "someuserid",
            "access_token": "someaccesstoken",
        }
        build_graph_api_url.return_value = expected_uri

        # Capture actual result
        actual = Threads.fetch_user_id_and_token(
            "https://some-auth-url.com",
            state="somestatetoken",
            config=self.configuration,
        )

        # Assertions
        MockOAuth2Session.assert_called_once_with(
            scope=self.configuration.scopes,
            state="somestatetoken",
            client_id=self.configuration.app_id,
            redirect_uri=self.configuration.redirect_uri,
        )

        build_graph_api_url.assert_called_once_with("oauth/access_token")

        mock_oauth2_session_instance.fetch_token.assert_called_once_with(
            expected_uri,
            authorization_response="https://some-auth-url.com",
            cert=ANY,
            include_client_id=True,
            client_secret="someapisecret",
        )

        self.assertEqual(actual, expected)

    @patch("pythreads.threads.datetime", wraps=datetime)
    @patch("pythreads.threads.get")
    @patch("pythreads.threads.Threads.build_graph_api_url")
    def test_fetch_long_lived_token_not_expired(
        self, build_graph_api_url, mock_get, mock_datetime
    ):
        # Mock build_graph_api_url
        expected_uri = "https://some-uri.com"
        build_graph_api_url.return_value = expected_uri

        # Mock get
        mock_response = MagicMock()
        mock_response.text = (
            '{"access_token": "somenewaccesstoken", "expires_in": 1000}'
        )
        mock_get.return_value = mock_response

        mock_datetime.now.return_value = self.time
        mock_datetime.now.timezone = timezone.utc

        expiration_window = 1000
        expiration_time = self.time + timedelta(seconds=expiration_window)

        expected = ("somenewaccesstoken", expiration_time)

        actual = Threads.fetch_long_lived_token(
            "someaccesstoken",
            expiration=expiration_time,
            config=self.configuration,
        )

        build_graph_api_url.assert_called_once_with(
            "access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_secret": self.configuration.api_secret,
            },
            access_token="someaccesstoken",
        )

        mock_get.assert_called_once_with(expected_uri, cert=ANY)

        self.assertEqual(actual, expected)

    @patch("pythreads.threads.datetime", wraps=datetime)
    @patch("pythreads.threads.get")
    @patch("pythreads.threads.Threads.build_graph_api_url")
    def test_fetch_long_lived_token_expired(
        self, build_graph_api_url, mock_get, mock_datetime
    ):
        build_graph_api_url.return_value = "https://some-uri.com"
        mock_get.return_value = "shouldn't be called"
        mock_datetime.now.return_value = self.time
        mock_datetime.now.timezone = timezone.utc

        expiration_time = self.time - timedelta(seconds=1)

        with self.assertRaises(ThreadsAccessTokenExpired):
            Threads.fetch_long_lived_token(
                "someaccesstoken",
                expiration=expiration_time,
                config=self.configuration,
            )

        build_graph_api_url.assert_not_called()
        mock_get.assert_not_called()

    @patch("pythreads.threads.datetime", wraps=datetime)
    @patch("pythreads.threads.get")
    @patch("pythreads.threads.Threads.build_graph_api_url")
    def test_refresh_long_lived_token_not_expired(
        self, build_graph_api_url, mock_get, mock_datetime
    ):
        # Mock build_graph_api_url
        expected_uri = "https://some-uri.com"
        build_graph_api_url.return_value = expected_uri

        # Mock get
        mock_response = MagicMock()
        mock_response.text = (
            '{"access_token": "somenewaccesstoken", "expires_in": 1000}'
        )
        mock_get.return_value = mock_response

        stubbed_now = self.time - timedelta(seconds=10)

        mock_datetime.now.return_value = stubbed_now
        mock_datetime.now.timezone = timezone.utc

        expiration_window = 1000
        expiration_time = stubbed_now + timedelta(seconds=expiration_window)

        expected = ("somenewaccesstoken", expiration_time)

        actual = Threads.refresh_long_lived_token(self.credentials)

        build_graph_api_url.assert_called_once_with(
            "refresh_access_token",
            params={
                "grant_type": "th_refresh_token",
            },
            access_token=self.credentials.access_token,
        )

        mock_get.assert_called_once_with(expected_uri, cert=ANY)

        self.assertEqual(actual, expected)

    @patch("pythreads.threads.datetime", wraps=datetime)
    @patch("pythreads.threads.get")
    @patch("pythreads.threads.Threads.build_graph_api_url")
    def test_refresh_long_lived_token_expired(
        self, build_graph_api_url, mock_get, mock_datetime
    ):
        build_graph_api_url.return_value = "https://some-uri.com"
        mock_get.return_value = "shouldn't be called"

        stubbed_now = self.time + timedelta(seconds=10)

        mock_datetime.now.return_value = stubbed_now
        mock_datetime.now.timezone = timezone.utc

        with self.assertRaises(ThreadsAccessTokenExpired):
            Threads.refresh_long_lived_token(self.credentials)

        build_graph_api_url.assert_not_called()
        mock_get.assert_not_called()
