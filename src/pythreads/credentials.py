# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List


class _JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self._object_hook, *args, **kwargs)

    def _object_hook(self, obj):
        ret = {}
        for key, value in obj.items():
            if key == "expiration":
                ret[key] = datetime.fromisoformat(value)
            else:
                ret[key] = value
        return ret


class _JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


@dataclass
class Credentials:
    user_id: str
    scopes: List[str]
    short_lived: bool
    access_token: str
    expiration: datetime

    def to_json(self) -> str:
        return json.dumps(asdict(self), cls=_JSONEncoder)

    @staticmethod
    def from_json(json_str: str) -> Credentials:
        data = json.loads(json_str, cls=_JSONDecoder)
        return Credentials(**data)

    def expires_in(self) -> int:
        """Number of seconds before these credentials' access token expires."""
        now = datetime.now(timezone.utc)
        delta = self.expiration - now
        seconds = int(delta.total_seconds())
        return seconds if seconds > 0 else 0

    def expired(self) -> bool:
        return True if self.expires_in() == 0 else False
