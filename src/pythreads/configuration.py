# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from typing import List


@dataclass
class Configuration:
    scopes: List[str]
    app_id: str
    api_secret: str
    redirect_uri: str

    def scopes_str(self):
        return ",".join(self.scopes)
