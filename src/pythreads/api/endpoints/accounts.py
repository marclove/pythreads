from __future__ import annotations

from typing import Any, Sequence

from pythreads.credentials import Credentials

from ..types import (
    DEFAULT_ACCOUNT_FIELDS,
    DEFAULT_PUBLISHING_LIMIT_FIELDS,
    PARAMS__FIELDS,
    AccountResponse,
    PublishingLimitResponse,
)
from ..transport import Transport


class AccountsService:
    def __init__(self, transport: Transport, credentials: Credentials) -> None:
        self.transport = transport
        self.credentials = credentials

    async def account(self, user_id: str = "me", fields: Sequence[str] = DEFAULT_ACCOUNT_FIELDS) -> AccountResponse:
        return await self.transport.get(user_id, {PARAMS__FIELDS: ",".join(fields)})

    async def publishing_limit(self, fields: Sequence[str] = DEFAULT_PUBLISHING_LIMIT_FIELDS) -> PublishingLimitResponse:
        user_id = self.credentials.user_id
        return await self.transport.get(
            f"{user_id}/threads_publishing_limit", {PARAMS__FIELDS: ",".join(fields)}
        )
