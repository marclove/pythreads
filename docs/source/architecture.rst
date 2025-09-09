Architecture Overview
=====================

Package Layout
--------------

- ``pythreads.api.client``: public API facade. Owns credentials, session
  management, and wires endpoint services. Backwards-compatible surface.
- ``pythreads.api.transport``: HTTP layer. Builds URLs (via
  ``Threads.build_graph_api_url``), validates access tokens, applies timeouts,
  retries with backoff, and normalizes JSON/text error handling.
- ``pythreads.api.endpoints.*``: endpoint services grouped by responsibility
  (accounts, threads, media, insights, moderation). Services build params and
  delegate HTTP to ``Transport``.
- ``pythreads.api.types``: enums, dataclasses, constants, and lightweight
  TypedDicts for common responses.
- ``pythreads.api.utils``: small helpers for timestamp and parameter casting.
- ``pythreads.threads``: OAuth and URL helpers for the Threads Graph API.

Design Principles
-----------------

- Single Responsibility: each service focuses on one domain area and is easy
  to test. The facade composes services; it doesn’t duplicate their logic.
- Consistent Transport: all HTTP goes through ``Transport`` for timeouts,
  retries, and error handling.
- Stronger Types: narrow return types where practical using TypedDicts;
  preserve dict-based flexibility where the schema is broad.
- Progressive Enhancement: iterators and options (timeouts, base_url, retries)
  are opt-in and non-breaking.

