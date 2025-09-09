from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, TypedDict, Dict, Any, List


# Python < 3.11 compatibility for StrEnum
try:  # pragma: no cover - import path when available
    from enum import StrEnum  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback for older Python
    class StrEnum(str, Enum):
        pass


class Field(StrEnum):
    AGE = "age"
    BREAKDOWN = "breakdown"
    CHILDREN = "children"
    CITY = "city"
    CONFIG = "config"
    COUNTRY = "country"
    DELETE_CONFIG = "delete_config"
    DELETE_QUOTA_USAGE = "delete_quota_usage"
    ERROR_MESSAGE = "error_message"
    FOLLOWERS_COUNT = "followers_count"
    FOLLOWER_DEMOGRAPHICS = "follower_demographics"
    GENDER = "gender"
    GIF_URL = "gif_url"
    HAS_REPLIES = "has_replies"
    HIDE_STATUS = "hide_status"
    ID = "id"
    IS_QUOTE_POST = "is_quote_post"
    IS_REPLY = "is_reply"
    IS_REPLY_OWNED_BY_ME = "is_reply_owned_by_me"
    LIKES = "likes"
    LOCATION_SEARCH_CONFIG = "location_search_config"
    LOCATION_SEARCH_QUOTA_USAGE = "location_search_quota_usage"
    MEDIA_PRODUCT_TYPE = "media_product_type"
    MEDIA_TYPE = "media_type"
    MEDIA_URL = "media_url"
    OWNER = "owner"
    PERMALINK = "permalink"
    POLL_ATTACHMENT = "poll_attachment"
    QUOTA_USAGE = "quota_usage"
    QUOTES = "quotes"
    REPLIED_TO = "replied_to"
    REPLIES = "replies"
    REPLY_AUDIENCE = "reply_audience"
    REPLY_CONFIG = "reply_config"
    REPLY_QUOTA_USAGE = "reply_quota_usage"
    REPOSTS = "reposts"
    ROOT_POST = "root_post"
    SHARES = "shares"
    SHORTCODE = "shortcode"
    STATUS = "status"
    TEXT = "text"
    THREADS_BIOGRAPHY = "threads_biography"
    THREADS_PROFILE_PICTURE_URL = "threads_profile_picture_url"
    THUMBNAIL_URL = "thumbnail_url"
    TIMESTAMP = "timestamp"
    TOPIC_TAG = "topic_tag"
    USERNAME = "username"
    VIEWS = "views"


DEFAULT_ACCOUNT_FIELDS = (
    Field.THREADS_BIOGRAPHY,
    Field.THREADS_PROFILE_PICTURE_URL,
    Field.USERNAME,
)

DEFAULT_PUBLISHING_LIMIT_FIELDS = (
    Field.CONFIG,
    Field.QUOTA_USAGE,
    Field.REPLY_CONFIG,
    Field.REPLY_QUOTA_USAGE,
)

DEFAULT_THREAD_FIELDS = (
    Field.CHILDREN,
    Field.ID,
    Field.IS_QUOTE_POST,
    Field.MEDIA_PRODUCT_TYPE,
    Field.MEDIA_TYPE,
    Field.MEDIA_URL,
    Field.OWNER,
    Field.PERMALINK,
    Field.SHORTCODE,
    Field.TEXT,
    Field.THUMBNAIL_URL,
    Field.TIMESTAMP,
    Field.USERNAME,
)

DEFAULT_REPLY_FIELDS = (
    Field.CHILDREN,
    Field.ID,
    Field.IS_QUOTE_POST,
    Field.MEDIA_PRODUCT_TYPE,
    Field.MEDIA_TYPE,
    Field.MEDIA_URL,
    Field.OWNER,
    Field.PERMALINK,
    Field.SHORTCODE,
    Field.TEXT,
    Field.THUMBNAIL_URL,
    Field.TIMESTAMP,
    Field.USERNAME,
)

DEFAULT_CONVERSATION_FIELDS = DEFAULT_REPLY_FIELDS

DEFAULT_METRIC_FIELDS = (
    Field.LIKES,
    Field.QUOTES,
    Field.REPLIES,
    Field.REPOSTS,
    Field.VIEWS,
)

USER_METRIC_TYPES = {
    Field.VIEWS,
    Field.LIKES,
    Field.REPLIES,
    Field.REPOSTS,
    Field.QUOTES,
    Field.FOLLOWERS_COUNT,
    Field.FOLLOWER_DEMOGRAPHICS,
}

UserMetricType = Literal[
    "views",
    "likes",
    "replies",
    "reposts",
    "quotes",
    "followers_count",
    "follower_demographics",
]

FOLLOWER_DEMOGRAPHIC_TYPES = {
    Field.AGE,
    Field.CITY,
    Field.COUNTRY,
    Field.GENDER,
}

FollowerDemographicType = Literal["age", "city", "country", "gender"]

MEDIA_TYPE__CAROUSEL = "CAROUSEL"
MEDIA_TYPE__IMAGE = "IMAGE"
MEDIA_TYPE__TEXT = "TEXT"
MEDIA_TYPE__VIDEO = "VIDEO"

PARAMS__ACCESS_TOKEN = "access_token"
PARAMS__AFTER = "after"
PARAMS__BEFORE = "before"
PARAMS__CHILDREN = "children"
PARAMS__CLIENT_ID = "client_id"
PARAMS__CONFIG = "config"
PARAMS__FIELDS = "fields"
PARAMS__HIDE = "hide"
PARAMS__IMAGE_URL = "image_url"
PARAMS__IS_CAROUSEL_ITEM = "is_carousel_item"
PARAMS__LIMIT = "limit"
PARAMS__MEDIA_TYPE = "media_type"
PARAMS__METRIC = "metric"
PARAMS__QUOTA_USAGE = "quota_usage"
PARAMS__REPLY_CONFIG = "reply_config"
PARAMS__REPLY_CONTROL = "reply_control"
PARAMS__REPLY_QUOTA_USAGE = "reply_quota_usage"
PARAMS__REPLY_TO_ID = "reply_to_id"
PARAMS__RESPONSE_TYPE = "response_type"
PARAMS__RETURN_URL = "return_url"
PARAMS__SCOPE = "scope"
PARAMS__SINCE = "since"
PARAMS__TEXT = "text"
PARAMS__UNTIL = "until"
PARAMS__USER_ID = "user_id"
PARAMS__VIDEO_URL = "video_url"


class MediaType(str, Enum):
    CAROUSEL = MEDIA_TYPE__CAROUSEL
    IMAGE = MEDIA_TYPE__IMAGE
    TEXT = MEDIA_TYPE__TEXT
    VIDEO = MEDIA_TYPE__VIDEO


class ReplyControl(str, Enum):
    ACCOUNTS_YOU_FOLLOW = "accounts_you_follow"
    EVERYONE = "everyone"
    MENTIONED_ONLY = "mentioned_only"


@dataclass
class Media:
    type: MediaType
    url: str


class PublishingStatus(str, Enum):
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
    FINISHED = "FINISHED"
    IN_PROGRESS = "IN_PROGRESS"
    PUBLISHED = "PUBLISHED"


class PublishingError(str, Enum):
    FAILED_DOWNLOADING_VIDEO = "FAILED_DOWNLOADING_VIDEO"
    FAILED_PROCESSING_AUDIO = "FAILED_PROCESSING_AUDIO"
    FAILED_PROCESSING_VIDEO = "FAILED_PROCESSING_VIDEO"
    INVALID_ASPEC_RATIO = "INVALID_ASPEC_RATIO"
    INVALID_BIT_RATE = "INVALID_BIT_RATE"
    INVALID_DURATION = "INVALID_DURATION"
    INVALID_FRAME_RATE = "INVALID_FRAME_RATE"
    INVALID_AUDIO_CHANNELS = "INVALID_AUDIO_CHANNELS"
    INVALID_AUDIO_CHANNEL_LAYOUT = "INVALID_AUDIO_CHANNEL_LAYOUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ContainerStatus:
    id: str
    status: PublishingStatus
    error: Optional[PublishingError] = None


# ---------- Typed response helpers (lightweight, partial schemas) ----------

JSONDict = Dict[str, Any]


class AccountResponse(TypedDict, total=False):
    username: str
    threads_biography: str
    threads_profile_picture_url: str


class PublishingQuotaConfig(TypedDict, total=False):
    quota_total: int
    quota_duration: int


class PublishingLimitEntry(TypedDict, total=False):
    config: PublishingQuotaConfig
    quota_usage: int
    reply_config: PublishingQuotaConfig
    reply_quota_usage: int


class PublishingLimitResponse(TypedDict):
    data: List[PublishingLimitEntry]


class InsightsValue(TypedDict, total=False):
    value: int
    end_time: str


class InsightsDataItem(TypedDict, total=False):
    name: str
    period: str
    values: List[InsightsValue]
    total_value: Dict[str, Any]
    id: str
    title: str
    description: str


class InsightsResponse(TypedDict, total=False):
    data: List[InsightsDataItem]
    paging: Dict[str, Any]
