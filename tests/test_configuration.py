# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import unittest

from pythreads.configuration import Configuration


class ConfigurationTest(unittest.TestCase):
    def test_scopes_str(self):
        config = Configuration(
            ["one", "two", "three"],
            app_id="app_id",
            api_secret="app_secret",
            redirect_uri="https://anywhere.net",
        )

        assert config.scopes_str() == "one,two,three"
