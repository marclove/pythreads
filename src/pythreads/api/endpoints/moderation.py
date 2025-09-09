from __future__ import annotations

from typing import Dict

from ..transport import Transport
from ..types import ManageReplyResponse, RequestOptions


class ModerationService:
    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    async def manage_reply(self, reply_id: str, hide: bool, *, request_options: RequestOptions | None = None) -> ManageReplyResponse:
        params: Dict[str, bool] = {"hide": hide}
        return await self.transport.post(f"{reply_id}/manage_reply", params, request_options)
