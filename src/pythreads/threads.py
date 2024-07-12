# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Union
from urllib.parse import urlencode

from dotenv import load_dotenv
from requests import Response, get
from requests_oauthlib import OAuth2Session

from pythreads.configuration import Configuration
from pythreads.credentials import Credentials

THREADS_GRAPH_API_VERSION = os.getenv("THREADS_GRAPH_API_VERSION")
GRAPH_API_BASE_URL = (
    f"https://graph.threads.net/{THREADS_GRAPH_API_VERSION}/"
    if THREADS_GRAPH_API_VERSION
    else "https://graph.threads.net/"
)

load_dotenv()


THREADS_SSL_CERT_FILEPATH = os.getenv("THREADS_SSL_CERT_FILEPATH", "")
THREADS_SSL_KEY_FILEPATH = os.getenv("THREADS_SSL_KEY_FILEPATH", "")
if not os.getenv("CI") and (
    THREADS_SSL_CERT_FILEPATH == "" or THREADS_SSL_KEY_FILEPATH == ""
):
    raise RuntimeError(
        "You must provide both an THREADS_SSL_CERT_FILEPATH and THREADS_SSL_KEY_FILEPATH in your environment for OAuth2 authentication and authorization"
    )

SSL_CREDENTIALS = (THREADS_SSL_CERT_FILEPATH, THREADS_SSL_KEY_FILEPATH)


class ThreadsAccessTokenExpired(RuntimeError): ...


class ThreadsAuthenticationError(RuntimeError): ...


class Threads:
    @staticmethod
    def build_graph_api_url(
        path, params: Union[dict, None] = None, access_token=None, base_url=None
    ):
        base_url = base_url or GRAPH_API_BASE_URL
        full_path = f"{base_url}{path}"
        query_components = []
        if params:
            query_components.append(f"{urlencode(params)}")
        if access_token:
            query_components.append(f"access_token={access_token}")
        query_fragment = "&".join(query_components)

        if len(query_fragment) > 0:
            url = "?".join([full_path, query_fragment])
        else:
            url = full_path
        return url

    """
    Authenticating with Threads is very simple. (NOTE: Ensure you've configured
    the necessary environment variables, as described in the README.)

    1.  Generate an authorization url and state key. Make the auth_url the
        href of a link or button and **store the state_key** (which is
        a randomly generated, opaque string used to mitigate CSRF attacks)
        somewhere you can reference later.

        >>> auth_url, state_key = Threads.authorization_url()

    2.  When the user clicks the link/button, they will be sent to Threads to
        authenticate and authorize your application access to their account.
        Upon authorization, they will be sent to your THREADS_REDIRECT_URI. At your
        THREADS_REDIRECT_URI endpoint, call `complete_authorization` with the full URL
        of the request to your server, which will contain an auth code:

        >>> credentials = Threads.complete_authorization(requested_url, state_key)

    3.  This automatically exchanges the auth code for a short-lived token and
        then exchanges the short-lived token for a long-lived token. It returns
        a `Credentials` object. The `Credentials` object can be serialized and
        deserialized to/from JSON, making it easy for you to persist it in the
        user's session or some other data store.

        >>> json = credentials.to_json()
        '{ "user_id": "someid", "scopes": ["threads_basic"], "short_lived": false, "access_token": "someaccesstoken", "expiration": "2024-06-23T18:25:43.511Z" }

        >>> Credentials.from_json(json)
        >>> Credentials(user_id="someid", scopes=["threads_basic"], short_lived=false, access_token="someaccesstoken", expiration=datetime.datetime(2024, 6, 23, 18, 25, 43, 121680, tzinfo=datetime.timezone.utc))

    4.  Long-lived tokens last 60 days, and are refreshable, as long as the
        token hasn't expired yet. Implement your own application logic to
        determine when it makes sense to refresh users' long-lived tokens, which
        you can do with:

        >>> refreshed_credentials = Threads.refresh_long_lived_token(old_credentials)

        A Credentials object's expiration is always stored in UTC time. It has
        a convenience method to check how many seconds before its token
        expires. For instance, a credentials object whose token will expire in
        two hours will return the following:

        >>> credentials.expires_in()
        7200

        This should make it easier to reason about whether the token needs to be
        refreshed or not.

    5.  You may now use credentials to make requests to the API:

        >>> async with Threads.API(credentials) as api:
        >>>     await api.threads()
        >>> api.replies('<thread-id>')
        >>> api.conversation('<thread-id>')
        >>> api.manage_reply('<reply-id>')

        See the API class's documentation for the full list of available
        methods. Each API method checks whether credentials have expired prior
        to making a request. If they have expired, a `ThreadsAccessTokenExpired`
        exception will be raised.

    """

    ALL_SCOPES = [
        "threads_basic",
        "threads_content_publish",
        "threads_manage_insights",
        "threads_manage_replies",
        "threads_read_replies",
    ]

    @staticmethod
    def load_configuration(
        scopes: Optional[List[str]] = None,
        app_id: Optional[str] = None,
        api_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Configuration:
        app_id = app_id or os.getenv("THREADS_APP_ID")
        api_secret = api_secret or os.getenv("THREADS_API_SECRET")
        redirect_uri = redirect_uri or os.getenv("THREADS_REDIRECT_URI")

        if app_id is None:
            raise ValueError("must define an THREADS_APP_ID env variable")

        if api_secret is None:
            raise ValueError("must define an THREADS_API_SECRET env variable")

        if redirect_uri is None:
            raise ValueError("must define an THREADS_REDIRECT_URI env variable")

        if scopes is None or len(scopes) == 0:
            scopes = Threads.ALL_SCOPES

        return Configuration(
            scopes=scopes,
            app_id=app_id,
            api_secret=api_secret,
            redirect_uri=redirect_uri,
        )

    @staticmethod
    def authorization_url(config: Optional[Configuration] = None) -> Tuple[str, str]:
        """Constructs an `authorization_url` and opaque `state` value.

        You must store the `state` value in the user's session so that you can
        retrieve it later and redirect the user to the `authorization_url`.
        When the user is redirected back to your `redirect_uri`, you will
        validate the authentication using `complete_authentication`.

        If you do not pass a Threads.Configuration instance, this method will
        load with the default configuration of all scopes and the THREADS_APP_ID,
        THREADS_API_SECRET, and THREADS_REDIRECT_URI environment variables.

        Args:
            config: [optional] A Threads.Configuration instance

        Returns:
            A tuple of (authorization_url, state), both being strings.

        Raises:
            OAuth2Error: An error occured in the OAuth2 flow. Check the
                `error` and `description` fields for more info.
        """
        configuration = config or Threads.load_configuration()

        session = OAuth2Session(
            scope=configuration.scopes_str(),
            client_id=configuration.app_id,
            redirect_uri=configuration.redirect_uri,
        )
        return session.authorization_url("https://threads.net/oauth/authorize")

    @staticmethod
    def complete_authorization(
        callback_url: str,
        state: str,
        long_lived_token: bool = True,
        config: Optional[Configuration] = None,
    ) -> Credentials:
        """state: the state string that was returned from the `authorization_url` method"""

        configuration = config or Threads.load_configuration()

        user_id, access_token, access_token_expiration = (
            Threads.fetch_user_id_and_token(
                request_url=callback_url, state=state, config=configuration
            )
        )

        credentials = Credentials(
            user_id=user_id,
            scopes=configuration.scopes,
            short_lived=True,
            access_token=access_token,
            expiration=access_token_expiration,
        )

        if not long_lived_token:
            return credentials

        access_token, access_token_expiration = Threads.fetch_long_lived_token(
            access_token=credentials.access_token,
            expiration=credentials.expiration,
            config=configuration,
        )
        credentials.short_lived = False
        credentials.access_token = access_token
        credentials.expiration = access_token_expiration

        return credentials

    @staticmethod
    def fetch_user_id_and_token(
        request_url: str, state: str, config: Optional[Configuration] = None
    ) -> Tuple[str, str, datetime]:
        """Exchanges authorization code for a short-lived OAuth2 API token (valid for 1 hour).

        Once you have redirected the user to the URL generated by the
        `authorization_url` method, Threads will redirect the user back to
        your `redirect_uri`, appending several request parameters to the
        URL. Call this method with that full request URL. It will extract
        the authorization code and state parameters, verify the state
        parameter to protect against CSRF attacks, and then call the
        Threads API to exchange the authorization code for a token.

        Args:
            request_url: the full request URL made by Threads to your redirect_uri

        Returns:
            A tuple of (user_id, access_token, access_token_expiration)

        Raises:
            OAuth2Error: An error occured in the OAuth2 flow. Check the
                `error` and `description` fields for more info.
        """
        configuration = config or Threads.load_configuration()

        session = OAuth2Session(
            scope=configuration.scopes,
            state=state,
            client_id=configuration.app_id,
            redirect_uri=configuration.redirect_uri,
        )

        uri = Threads.build_graph_api_url("oauth/access_token")
        response = session.fetch_token(
            uri,
            authorization_response=request_url,
            cert=SSL_CREDENTIALS,
            include_client_id=True,
            client_secret=configuration.api_secret,
        )

        if "access_token" not in response:
            raise ThreadsAuthenticationError(
                f"Response from Threads API ({response}) did not include expected `access_token` key"
            )
        if "user_id" not in response:
            raise ThreadsAuthenticationError(
                f"Response from Threads API ({response}) did not include expected `user_id` key"
            )

        return (
            response["user_id"],
            response["access_token"],
            datetime.now(timezone.utc) + timedelta(hours=1),
        )

    @staticmethod
    def fetch_long_lived_token(
        access_token: str,
        expiration: datetime,
        config: Optional[Configuration] = None,
    ) -> Tuple[str, datetime]:
        if expiration <= datetime.now(timezone.utc):
            raise ThreadsAccessTokenExpired(
                "The session's short-lived access token has expired, so we are unable to exchange it for a long-lived access token. You must reauthenticate the user with Threads."
            )

        configuration = config or Threads.load_configuration()

        uri = Threads.build_graph_api_url(
            "access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_secret": configuration.api_secret,
            },
            access_token=access_token,
        )
        response = get(uri, cert=SSL_CREDENTIALS)
        return Threads.__handle_long_lived_access_token_response(response)

    @staticmethod
    def refresh_long_lived_token(
        credentials: Credentials,
    ) -> Tuple[str, datetime]:
        if credentials.short_lived:
            raise TypeError(
                "You are attempting to refresh a short-lived access token. Only long-lived access tokens may be refreshed. Instead, call `fetch_long_lived_token`."
            )

        if credentials.expiration <= datetime.now(timezone.utc):
            raise ThreadsAccessTokenExpired(
                "The long-lived access token has expired, so we are unable to refresh it. You must reauthenticate the user with Threads."
            )

        uri = Threads.build_graph_api_url(
            "refresh_access_token",
            params={"grant_type": "th_refresh_token"},
            access_token=credentials.access_token,
        )
        response = get(uri, cert=SSL_CREDENTIALS)
        return Threads.__handle_long_lived_access_token_response(response)

    @staticmethod
    def __handle_long_lived_access_token_response(
        response: Response,
    ) -> Tuple[str, datetime]:
        resp = json.loads(response.text)

        if "access_token" not in resp:
            raise ThreadsAuthenticationError(
                f"Response from Threads API({response}) did not include expected `access_token` key"
            )
        if "expires_in" not in resp:
            raise ThreadsAuthenticationError(
                f"Response from Threads API({response}) did not include expected `expires_in` key"
            )

        return (
            resp["access_token"],
            datetime.now(timezone.utc) + timedelta(seconds=resp["expires_in"]),
        )
