from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pythreads.credentials import Credentials

from ..errors import ThreadsInvalidParameter, ThreadsResponseError
from ..transport import Transport
from ..types import (
    ContainerResponse,
    ContainerStatus,
    Field,
    Media,
    MediaType,
    PARAMS__CHILDREN,
    PARAMS__FIELDS,
    PARAMS__IMAGE_URL,
    PARAMS__IS_CAROUSEL_ITEM,
    PARAMS__MEDIA_TYPE,
    PARAMS__REPLY_CONTROL,
    PARAMS__REPLY_TO_ID,
    PARAMS__TEXT,
    PARAMS__VIDEO_URL,
    PublishingError,
    PublishingStatus,
    ReplyControl,
    ThreadResponse,
)


class MediaService:
    def __init__(self, transport: Transport, credentials: Credentials) -> None:
        self.transport = transport
        self.credentials = credentials

    async def create_container(
        self,
        text: Optional[str] = None,
        media: Optional[Media] = None,
        reply_control: ReplyControl = ReplyControl.EVERYONE,
        reply_to_id: Optional[str] = None,
        is_carousel_item: bool = False,
        *, request_options: dict | None = None) -> str:
        params: Dict[str, Union[str, bool, List[str], None]] = {
            PARAMS__REPLY_CONTROL: reply_control.value,
        }

        if text:
            params[PARAMS__TEXT] = text
            params[PARAMS__MEDIA_TYPE] = MediaType.TEXT.value

        if reply_to_id:
            params[PARAMS__REPLY_TO_ID] = reply_to_id

        if is_carousel_item:
            params[PARAMS__IS_CAROUSEL_ITEM] = is_carousel_item

        if media and media.type == MediaType.VIDEO:
            params[PARAMS__MEDIA_TYPE] = media.type.value
            params[PARAMS__VIDEO_URL] = media and media.url
        elif media and media.type == MediaType.IMAGE:
            params[PARAMS__MEDIA_TYPE] = media.type.value
            params[PARAMS__IMAGE_URL] = media and media.url

        user_id = self.credentials.user_id
        response: Dict[str, Any] = await self.transport.post(f"{user_id}/threads", params, request_options)
        if "id" not in response:
            raise ThreadsResponseError(response)
        return response["id"]

    async def create_carousel_container(
        self,
        containers: List[ContainerStatus],
        text: Optional[str] = None,
        reply_control: ReplyControl = ReplyControl.EVERYONE,
        reply_to_id: Optional[str] = None,
        *, request_options: dict | None = None) -> str:
        num_media = len(containers)
        if num_media < 2 or num_media > 10:
            raise ThreadsInvalidParameter("a carousel post requires 2-10 media items")

        if any([item.status != PublishingStatus.FINISHED for item in containers]):
            raise ThreadsInvalidParameter(
                "all published_media must have a status of `FINISHED` before adding them to a carousel container"
            )

        child_ids = [item.id for item in containers]
        children = ",".join(child_ids)

        params: Dict[str, Union[str, bool, List[str], None]] = {
            PARAMS__MEDIA_TYPE: MediaType.CAROUSEL.value,
            PARAMS__CHILDREN: children,
            PARAMS__REPLY_CONTROL: reply_control.value,
        }

        if text:
            params[PARAMS__TEXT] = text

        if reply_to_id:
            params[PARAMS__REPLY_TO_ID] = reply_to_id

        user_id = self.credentials.user_id
        response: Dict[str, Any] = await self.transport.post(f"{user_id}/threads", params, request_options)
        if "id" not in response:
            raise ThreadsResponseError(response)
        return response["id"]

    async def container_status(self, media_id: str, *, request_options: dict | None = None) -> ContainerStatus:
        result: Dict[str, Any] = await self.transport.get(
            f"{media_id}",
            {
                PARAMS__FIELDS: ",".join(
                    [
                        Field.ID,
                        Field.STATUS,
                        Field.ERROR_MESSAGE,
                    ]
                )
            }, request_options
        )

        status_str = result.get("status", PublishingStatus.ERROR)
        status = PublishingStatus[status_str]

        error = None
        error_str = result.get("error_message", None)
        if error_str and error_str != "":
            error = PublishingError[error_str]

        media = ContainerStatus(id=result["id"], status=status, error=error)
        return media

    async def publish_container(self, container_id: str, *, request_options: dict | None = None) -> str:
        user_id = self.credentials.user_id
        response: Dict[str, Any] = await self.transport.post(
            f"{user_id}/threads_publish", {"creation_id": container_id}, request_options
        )
        if "id" not in response:
            raise ThreadsResponseError(response)
        return response["id"]

    async def container(self, container_id: str, *, request_options: dict | None = None) -> ContainerResponse:
        return await self.transport.get(
            f"{container_id}",
            {
                PARAMS__FIELDS: ",".join(
                    [
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
                    ]
                )
            }, request_options
        )

    async def thread(self, thread_id: str, *, request_options: dict | None = None) -> ThreadResponse:
        return await self.container(container_id=thread_id, request_options=request_options)
