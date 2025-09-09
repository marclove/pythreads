from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence, Union

from pythreads.credentials import Credentials

from ..errors import ThreadsInvalidParameter
from ..transport import Transport
from ..types import (
    DEFAULT_METRIC_FIELDS,
    FOLLOWER_DEMOGRAPHIC_TYPES,
    USER_METRIC_TYPES,
    FollowerDemographicType,
    PARAMS__FIELDS,
    PARAMS__METRIC,
    Field,
    InsightsResponse,
    RequestOptions,
)
from ..utils import ts_to_str


class InsightsService:
    def __init__(self, transport: Transport, credentials: Credentials) -> None:
        self.transport = transport
        self.credentials = credentials

    async def user_insights(
        self,
        metrics: Union[str, List[str]],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        breakdown: Optional[FollowerDemographicType] = None,
        *, request_options: RequestOptions | None = None) -> InsightsResponse:
        if isinstance(metrics, str):
            metrics = [metrics]

        requested_metrics = set(metrics)

        invalid_metrics = requested_metrics.difference(USER_METRIC_TYPES)
        if len(invalid_metrics) > 0:
            raise ThreadsInvalidParameter(
                f"Invalid metrics provided: {', '.join(invalid_metrics)}"
            )

        if (
            Field.FOLLOWER_DEMOGRAPHICS in requested_metrics
            and breakdown not in FOLLOWER_DEMOGRAPHIC_TYPES
        ):
            raise ThreadsInvalidParameter(
                "follower_demographics metric requires a breakdown value"
            )

        params: Dict[str, str | float] = {PARAMS__METRIC: ",".join(metrics)}
        if since:
            params["since"] = int(since.timestamp())
        if until:
            params["until"] = int(until.timestamp())
        if breakdown:
            params["breakdown"] = breakdown

        user_id = self.credentials.user_id
        return await self.transport.get(f"{user_id}/threads_insights", params, request_options)

    async def insights(
        self,
        thread_id: str,
        metric: Sequence[str] = DEFAULT_METRIC_FIELDS,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        *, request_options: RequestOptions | None = None) -> InsightsResponse:
        params: Dict[str, str] = {PARAMS__FIELDS: ",".join(metric)}
        if since:
            params["since"] = ts_to_str(since)
        if until:
            params["until"] = ts_to_str(until)

        return await self.transport.get(f"{thread_id}/insights", params, request_options)
