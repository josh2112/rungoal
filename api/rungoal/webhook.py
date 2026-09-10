import asyncio
import datetime
import logging
from enum import StrEnum
from typing import Annotated, Literal, cast
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, Header, HTTPException, Response, status
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel

from .crud import get_user_by_health_id
from .database import get_db
from .models import SyncRequest
from .sync_operation import get_sync_operation, sync_start


class WebhookSubscriptionVerification(BaseModel):
    type: Literal["verification"]


class Operation(StrEnum):
    UPSERT = "UPSERT"
    DELETE = "DELETE"


class PhysicalTimeInterval(BaseModel):
    startTime: datetime.datetime
    endTime: datetime.datetime


class NotificationInterval(BaseModel):
    physicalTimeInterval: PhysicalTimeInterval | None


class NotificationItem(BaseModel):
    healthUserId: str
    operation: Operation
    dataType: str
    intervals: list[NotificationInterval]


class WebhookNotification(BaseModel):
    data: NotificationItem


logger = logging.getLogger("uvicorn.error")


async def _proceess_webhook_notifications(notifications: list[WebhookNotification]):
    logger.info("Webhook triggered. Waiting 60 seconds for GPS datapoints to be processed...")
    await asyncio.sleep(60)

    with get_db() as db:
        for n in notifications:
            if n.data.dataType != "exercise" or not (
                user := get_user_by_health_id(db, n.data.healthUserId)
            ):
                continue

            user_id = cast(int, user.id)

            for interval in [
                i.physicalTimeInterval for i in n.data.intervals if i.physicalTimeInterval
            ]:
                logger.info(f"Syncing interval {interval.startTime} -> {interval.endTime}")
                if sync_op := get_sync_operation(user_id):
                    await sync_op.done.wait()
                if sync_op := await sync_start(
                    user_id,
                    SyncRequest(
                        from_=interval.startTime, to=interval.endTime, include_runtracker=False
                    ),
                    # This only matters for runtracker imports
                    timezone=ZoneInfo("UTC"),
                ):
                    await sync_op.done.wait()


def process_webhook_request(
    payload: WebhookSubscriptionVerification | list[WebhookNotification],
    background_tasks: BackgroundTasks,
    authorization: Annotated[str | None, Header()] = None,
):

    # First, reject if auth doesn't match what we provided when creating the subscription

    scheme, token = get_authorization_scheme_param(authorization)
    if (
        scheme or ""
    ).lower() != "bearer" and token != "EkE3ZibMkH4snCqnHsjpHNJM_mPHZpdNnSXes-85MGo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid verification secret",
        )

    if isinstance(payload, WebhookSubscriptionVerification):
        return Response(status_code=status.HTTP_201_CREATED)
    else:
        background_tasks.add_task(_proceess_webhook_notifications, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
