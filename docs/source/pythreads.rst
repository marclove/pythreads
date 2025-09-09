API Module
--------------------

.. automodule:: pythreads.api
   :members:
   :undoc-members:
   :show-inheritance:

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
