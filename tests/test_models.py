# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

from pythreads.api.models import InsightsResponseModel


def test_insights_pydantic_validation():
    raw = {
        "data": [
            {
                "name": "likes",
                "period": "day",
                "values": [{"value": 10, "end_time": "2024-07-11T07:00:00+0000"}],
                "title": "Likes",
                "description": "The number of likes on your post.",
                "id": "someid/insights/likes/day",
            }
        ]
    }

    model = InsightsResponseModel.model_validate(raw)
    assert model.data is not None
    assert model.data[0].name == "likes"
