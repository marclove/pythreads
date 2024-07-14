# PyThreads

[![PyPI - Version](https://img.shields.io/pypi/v/pythreads.svg)](https://pypi.org/project/pythreads)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pythreads.svg)](https://pypi.org/project/pythreads)
![Code Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen)

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
- [Roadmap](#roadmap)
- [License](#license)

## Installation

```console
pip install pythreads
```

## Environment Variables

You will need to create an app in the [developer console](https://developers.facebook.com/docs/development/create-an-app/threads-use-case) which has the Threads Use Case enabled and add the the following variables to your environment. The redirect URI needs to be the URL in your application where you call the `complete_authorization` method.

```
THREADS_REDIRECT_URI=
THREADS_APP_ID=
THREADS_API_SECRET=
```

## Authentication & Authorization

Authenticating with PyThreads is very simple:

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
    URL of the request made to your server (which contains the auth code) and
    the `state_key`, which was generated in the previous step:

    ```python
    credentials = Threads.complete_authorization(requested_url, state_key)
    ```

3.  This method automatically exchanges the auth code for a short-lived token
    and immediately exchanges the short-lived token for a long-lived token.
    The method returns `Credentials` object, which contains this long-lived
    token and details about the user. The `Credentials` object can be
    serialized and deserialized to/from JSON, making it easy for you to
    persist it in some data store or store it encrypted in the user's
    session.

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

5.  Long-lived tokens last 60 days, and are refreshable, as long as the
    token hasn't expired yet. Implement your own application logic to
    determine when it makes sense to refresh users' long-lived tokens, which
    you can do with:

    ```python
    refreshed_credentials = Threads.refresh_long_lived_token(old_credentials)
    ```

    A `Credentials` object has convenience methods to make it easier for
    you to determine whether the token is still valid and how much longer
    it is valid for.

    ```python
    credentials.expired()
    >>> False

    credentials.expires_in()
    >>> 7200 # seconds
    ```

    Of course, you can always check the expiration time directly. It is
    stored in UTC time:

    ```python
    credentials.expiration
    >>> datetime(2024, 7, 11, 10, 50, 32, 870181, tzinfo=datetime.timezone.utc)
    ```

    If you call an API method using expired credentials, a `ThreadsAccessTokenExpired`
    exception will be raised. 

## Making Requests

Once you have a valid `Credentials` object, you can use an `API` object to
call the Threads API. The `API` object uses an `aiohttp.ClientSession` to make 
async HTTP calls. You may either supply your own session or let the library
create and manage one itself.

If you do not supply your own session, PyThreads will create one and take
responsibility for closing it. You must use the `API` object as an async
context manager if you want it to manage a session for you:

```python
# Retrieve the user's credentials from whereever you're storing them:
credentials = Credentials.from_json(stored_json)

async with API(credentials=credentials) as api:
    await api.threads()
```

If you want to create and manage your own session (e.g. you're already
using `aiohttp` elsewhere in your application and want to use a single
session for all requests):

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

## API Methods

Better documentation is coming, but for now, you can browse the methods
in [api.py](src/pythreads/api.py).

Most of the methods follow [Meta's API](https://developers.facebook.com/docs/threads)
closely, with required/optional arguments matching API required/optional
parameters.

### Making a text-only post
Making a text-only post is a two-step process. Create a container and then
publish it:

```python
async with API(credentials) as api:
    container_id = await api.create_container("A text-only post")
    result_id = await api.publish_container(container_id)
    # container_id == result_id
```

### Making a post with a single media file
Making a post with a single media file is also a two-step process. Create a
container with the media file and any post text and then publish it:

```python
async with API(credentials) as api:
    # Create a video container. You must put media resources at a publicly-accessible URL where Threads can download it.
    a_video = Media(type=MediaType.VIDEO, url="https://mybucket.s3.amazonaws.com/video.mp4")
    container_id = await api.create_container(media=a_video)

    # Video containers need to complete processing before you can publish them
    await asyncio.sleep(15)

    # Check the status to see if it's finished processing
    status = await api.container_status(container_id)
    # >>> ContainerStatus(id='14781862679302648', status=<PublishingStatus.FINISHED: 'FINISHED'>, error=None)

    # Publish the video container
    result_id = await api.publish_container(container_id)
    # container_id == result_id
```

### Making a carousel post
Making a post with a media carousel is a three-step process. Create a container
for each media file in the carousel, then create a container for the carousel
(attaching the media containers as children), and publish the carousel container:

```python
async with API(self.credentials) as api:
    # Create an image container
    an_image = Media(type=MediaType.IMAGE, url="https://mybucket.s3.amazonaws.com/python.png")
    image_id = await api.create_container(media=an_image, is_carousel_item=True)

    # Create a video container
    a_video = Media(type=MediaType.VIDEO, url="https://mybucket.s3.amazonaws.com/video.mp4")
    video_id = await api.create_container(media=a_video, is_carousel_item=True)

    # Video containers need to complete processing before you can publish them
    await asyncio.sleep(15)

    # Check the status to see if the containers are finished processing
    status_1 = await api.container_status(image_id)
    status_2 = await api.container_status(video_id)
    # >>> ContainerStatus(id='14781862679302648', status=<PublishingStatus.FINISHED: 'FINISHED'>, error=None)
    # >>> ContainerStatus(id='14823646267930264', status=<PublishingStatus.FINISHED: 'FINISHED'>, error=None)

    # Create the carousel container, which wraps the media containers as children
    carousel_id = await api.create_carousel_container(containers=[status_1, status_2], text="Here's a carousel")

    await asyncio.sleep(15)

    # Check the carousel container status
    carousel_status = await api.container_status(carousel_id)
    # >>> ContainerStatus(id='15766826793021848', status=<PublishingStatus.FINISHED: 'FINISHED'>, error=None)

    # Publish the carousel container
    result_id = await api.publish_container(carousel_id)
    # carousel_id == result_id
```

A few key things to point out above:

1. Creating media containers requires you to put the image or video at a
publicly-accessible URL. Meta retrieves the media file from that URL.

1. When creating a media container with a video, Threads requires you to
wait for the video to be processed before you can either publish them or
attach them to a carousel container. This can take seconds or minutes.

You are **strongly encouraged** to read Meta's documentation regarding the posting
process:

- [Post to Threads](https://developers.facebook.com/docs/threads/posts)
- [Understanding Container Status](https://developers.facebook.com/docs/threads/troubleshooting#publishing-does-not-return-a-media-id)

## Roadmap
- [ ] Improve documentation of `API` methods and publish the docs.
- [ ] Type the return values of the `API` methods. They currently all return `Any`.
- [ ] Add integration with S3 and R2 storage. The Threads API doesn't take media uploads directly. You have to upload files to a publicly accessible URL and pass the URL in the API response. This integration would handle the upload to cloud storage and passing of the URL to the Threads API for you.
- [ ] Explore adding JSON fixtures of expected responses to specs.

## License

`pythreads` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
