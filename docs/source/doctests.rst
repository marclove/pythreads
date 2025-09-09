Doctests
========

These quick doctests validate small, self-contained pieces of functionality.

Utils
-----

.. doctest::

   >>> from datetime import datetime, timezone
   >>> from pythreads.api.utils import ts_to_str, iso_date_or_str
   >>> ts_to_str(datetime(1970, 1, 1, tzinfo=timezone.utc))
   '0'
   >>> iso_date_or_str('2024-01-01')
   '2024-01-01'

Pydantic Models
---------------

.. doctest::

   >>> from pythreads.api.models import InsightsResponseModel
   >>> raw = {"data": [{"name": "likes", "period": "day", "values": [{"value": 1}]}]}
   >>> model = InsightsResponseModel.model_validate(raw)
   >>> model.data[0].name
   'likes'

