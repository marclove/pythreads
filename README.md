# PyThreads

[![PyPI - Version](https://img.shields.io/pypi/v/pythreads.svg)](https://pypi.org/project/pythreads)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pythreads.svg)](https://pypi.org/project/pythreads)
![Code Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)

PyThreads is a Python wrapper for Meta's Threads API. It is still in beta, 
but is well-tested and covers all the published endpoints documented by Meta.

Since it is in pre-release, the API is not yet guaranteed to be stable. Once 
there's been some opportunity to weed out any bugs and identify any DX 
inconveniences, a v1 with a stable API will be released. This project 
follows [Semantic Versioning](https://semver.org/).

-----

## Table of Contents

- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Authentication & Authorization](#authentication--authorization)
- [Making Requests](#making-requests)
- [API Methods](#api-methods)
- [License](#license)

## Installation

```console
pip install pythreads
```

## Environment Variables

You must make the following environment variables available:

```
THREADS_REDIRECT_URI=
THREADS_APP_ID=
THREADS_API_SECRET=
```

You will need to create an app in the [developer console](https://developers.facebook.com/docs/development/create-an-app/threads-use-case) which has the Threads Use Case enabled and add the the following variables to your environment. The redirect URI needs to be the URL in your application where you call the `complete_authorization` method.

## Authentication & Authorization

Authenticating with Threads is very simple:

1.  Generate an authorization url and state key. Make the auth_url the
    href of a link or button and **store the state_key** (which is
    a randomly generated, opaque string used to mitigate CSRF attacks)
    somewhere you can reference later when Threads redirects the user back
    to your redirect URI.

    ```python
    auth_url, state_key = Threads.authorization_url()
    ```

2.  When the user clicks the link/button, they will be sent to Threads to
    authenticate and authorize your application access to their account.
    Upon authorization, they will be sent to your THREADS_REDIRECT_URI. At your
    THREADS_REDIRECT_URI endpoint, call `complete_authorization` with the full
    URL of the request made to your server, which will contain an auth code. You
    must also pass the `state_key`, which was generated in the previous step:

    ```python
    credentials = Threads.complete_authorization(requested_url, state_key)
    ```

3.  This automatically exchanges the auth code for a short-lived token and
    then exchanges the short-lived token for a long-lived token. It returns
    a `Credentials` object. The `Credentials` object can be serialized and
    deserialized to/from JSON, making it easy for you to persist it in the
    user's session or some other data store.

    ```python
    json = credentials.to_json()
    ```
    ```json
    { 
      "user_id": "someid", 
      "scopes": ["threads_basic"], 
      "short_lived": false, 
      "access_token": "someaccesstoken", 
      "expiration": "2024-06-23T18:25:43.511Z"
    }
    ```

    ```python
    Credentials.from_json(json)

    # or

    Credentials(
        user_id="someid", 
        scopes=["threads_basic"], 
        short_lived=false, 
        access_token="someaccesstoken", 
        expiration=datetime.datetime(2024, 6, 23, 18, 25, 43, 121680, tzinfo=datetime.timezone.utc)
    )
    ```

4.  Long-lived tokens last 60 days, and are refreshable, as long as the
    token hasn't expired yet. Implement your own application logic to
    determine when it makes sense to refresh users' long-lived tokens, which
    you can do with:

    ```python
    refreshed_credentials = Threads.refresh_long_lived_token(old_credentials)
    ```

    A Credentials object's expiration is always stored in UTC time. It has
    a convenience method to check how many seconds before its token
    expires. For instance, a credentials object whose token will expire in
    two hours will return the following:

    ```python
    credentials.expires_in()
    >>> 7200
    ```

    This should make it easier to reason about whether the token needs to be
    refreshed or not.

## Making Requests

Once you have a valid `Credentials` object, you can use an `API` object to
call the Threads API. The `API` object uses an `aiohttp.ClientSession` to make 
async HTTP calls. You may either supply your own session or let the library
create and manage one itself.

If you want the library to create a session and manage itself:

```python
# Create an `aiohttp.ClientSession` at some point:
session = aiohttp.ClientSession()

# Retrieve the user's credentials from whereever you're storing them:
credentials = Credentials.from_json(stored_json)

api = API(credentials=credentials, session=session)
threads = await api.threads()

# If you supply your own session, you are responsible for closing it:
session.close()
```

If you do not supply your own session, PyThreads will create one and take
responsibility for closing it. You must use the `API` object as an async
context manager if you want it to manage a session for you:

```python
# Retrieve the user's credentials from whereever you're storing them:
credentials = Credentials.from_json(stored_json)

async with API(credentials=credentials) as api:
    await api.threads()
```

## API Methods

Better documentation is coming, but for now, you can browse the methods in [api.py](src/pythreads/api.py).

Other than the `publish` method, which provides a high-level interface for creating a new Thread of any type with any kind of attachment, the rest of the methods follow [Meta's API](https://developers.facebook.com/docs/threads) fairly closely.

## License

`pythreads` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
