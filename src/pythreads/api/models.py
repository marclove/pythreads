from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AccountModel(BaseModel):
    username: Optional[str] = None
    threads_biography: Optional[str] = None
    threads_profile_picture_url: Optional[str] = None


class PublishingQuotaConfigModel(BaseModel):
    quota_total: Optional[int] = None
    quota_duration: Optional[int] = None


class PublishingLimitEntryModel(BaseModel):
    config: Optional[PublishingQuotaConfigModel] = None
    quota_usage: Optional[int] = None
    reply_config: Optional[PublishingQuotaConfigModel] = None
    reply_quota_usage: Optional[int] = None


class PublishingLimitResponseModel(BaseModel):
    data: List[PublishingLimitEntryModel]


class InsightsValueModel(BaseModel):
    value: Optional[int] = None
    end_time: Optional[str] = None


class InsightsDataItemModel(BaseModel):
    name: Optional[str] = None
    period: Optional[str] = None
    values: Optional[List[InsightsValueModel]] = None
    total_value: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class InsightsResponseModel(BaseModel):
    data: Optional[List[InsightsDataItemModel]] = None
    paging: Optional[Dict[str, Any]] = None

