# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import datetime

import pytest

from pythreads.credentials import Credentials


@pytest.fixture
def credentials():
    return Credentials(
        user_id="userid",
        scopes=["scope1", "scope2"],
        short_lived=False,
        access_token="accesstoken",
        expiration=datetime.datetime(2024, 6, 30, 0, 0, 0, 0, datetime.timezone.utc),
    )


def test_serialization(credentials):
    expected = '{"user_id": "userid", "scopes": ["scope1", "scope2"], "short_lived": false, "access_token": "accesstoken", "expiration": "2024-06-30T00:00:00+00:00"}'
    assert credentials.to_json() == expected


def test_deserialization(credentials):
    expected = credentials
    json = '{"user_id": "userid", "scopes": ["scope1", "scope2"], "short_lived": false, "access_token": "accesstoken", "expiration": "2024-06-30T00:00:00+00:00"}'
    assert Credentials.from_json(json) == expected


def test_expires_in(credentials):
    credentials.expiration = datetime.datetime.now(
        datetime.timezone.utc
    ) + datetime.timedelta(seconds=10)
    assert credentials.expires_in() == 9  # some milliseconds will have passed


def test_expired(credentials):
    credentials.expiration = datetime.datetime.now(datetime.timezone.utc)
    assert credentials.expired()  # some milliseconds will have passed
