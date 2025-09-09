API Module
--------------------

.. automodule:: pythreads.api
   :members:
   :undoc-members:
   :show-inheritance:

Endpoints
--------------------

These modules implement the endpoint groups used by the API facade. They are
organized by responsibility and delegate HTTP to a shared Transport.

.. automodule:: pythreads.api.endpoints.accounts
   :members:
   :undoc-members:

.. automodule:: pythreads.api.endpoints.threads
   :members:
   :undoc-members:

.. automodule:: pythreads.api.endpoints.media
   :members:
   :undoc-members:

.. automodule:: pythreads.api.endpoints.insights
   :members:
   :undoc-members:

.. automodule:: pythreads.api.endpoints.moderation
   :members:
   :undoc-members:

API Options
--------------------

The ``API`` client accepts several optional keyword arguments that control
behavior:

- ``timeout``: float seconds or ``aiohttp.ClientTimeout`` (default: 30)
- ``base_url``: override the base Graph API URL (default: Threads base)
- ``retries``: number of retries for transient HTTP statuses like 429/5xx (default: 0)
- ``backoff_base``: initial backoff seconds for retries (default: 0.5)
- ``backoff_max``: maximum backoff seconds (default: 4.0)

Example::

   async with API(credentials, timeout=10, base_url="https://graph.threads.net/", retries=3) as api:
       await api.threads()

Configuration Module
------------------------------

.. automodule:: pythreads.configuration
   :members:
   :undoc-members:
   :show-inheritance:

Credentials Module
----------------------------

.. automodule:: pythreads.credentials
   :members:
   :undoc-members:
   :show-inheritance:

Threads Module
------------------------

.. automodule:: pythreads.threads
   :members:
   :undoc-members:
   :show-inheritance:
