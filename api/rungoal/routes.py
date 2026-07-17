import asyncio
from collections.abc import AsyncIterable
from datetime import datetime
from typing import Annotated, cast
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, Query, Response, status
from fastapi.sse import EventSourceResponse
from jose import JWTError
from pydantic import BaseModel, Field

from rungoal import auth, crud
from rungoal.deps import DepDb, DepUser
from rungoal.models import (
    AccessToken,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    GoogleApiAuthCode,
    Run,
    RunResponse,
    User,
    UserResponse,
)
from rungoal.sync_operation import SyncState, sync_start, sync_status, sync_stream

api = APIRouter(prefix="/api")

used_refresh_tokens = auth.UsedRefreshTokens()


# Generates a new token pair for the given email address, sets the refresh
# token as an HTTP-only cookie and returns the access token.
def _set_tokens(email: str, response: Response) -> AccessToken:
    access_token, refresh_token = auth.generate_token_pair(email)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    return AccessToken(access_token=access_token)


@api.post("/auth/google", tags=["Auth"])
def google_auth(auth_code: GoogleApiAuthCode, db: DepDb, response: Response) -> AccessToken:
    # Get full user info with Google API tokens
    google_user = auth.get_google_user(auth_code)
    user = crud.get_user_by_email(db, google_user.email)
    if user:
        # Update the existing user with the latest data (keeping the existing ID)
        db.merge(User(id=user.id, **google_user.model_dump()))
        db.commit()
    else:
        user = crud.create_user(db, google_user)

    return _set_tokens(user.email, response)


@api.post("/auth/refresh", tags=["Auth"])
def refresh_token(
    db: DepDb, response: Response, refresh_token: Annotated[str | None, Cookie()] = None
) -> AccessToken:
    if not refresh_token or not (token := auth.refresh_token_decode(refresh_token)):
        raise JWTError("Refresh token invalid")

    # Will throw an exception if the refresh token has already been used
    used_refresh_tokens.add(refresh_token, token.expires)

    user = crud.get_user_by_email(db, token.subject)
    if not user:
        raise JWTError("Refresh token invalid")

    return _set_tokens(user.email, response)


@api.get("/auth/logout", tags=["Auth"])
def logout(response: Response):
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")


@api.get("/user/me", response_model=UserResponse)
def get_user(user: DepUser):
    return user


@api.get("/sync/status")
def get_sync_status(user: DepUser) -> SyncState:
    return sync_status(cast(int, user.id))


@api.get("/sync/stream", response_class=EventSourceResponse)
async def get_sync_stream(user: DepUser) -> AsyncIterable[SyncState]:
    async for p in sync_stream(cast(int, user.id)):
        yield p
    await asyncio.sleep(0.2)  # Give the sync-complete message a chance to be sent


class SyncParams(BaseModel):
    from_: datetime | None = Field(alias="from", default=None)
    to: datetime | None = None
    runtracker_timezone: str | None = None


@api.post("/sync")
async def start_sync(user: DepUser, params: SyncParams):
    await sync_start(
        cast(int, user.id),
        params.from_,
        params.to,
        ZoneInfo(params.runtracker_timezone) if params.runtracker_timezone else None,
    )
    return status.HTTP_202_ACCEPTED


@api.get("/goals")
def get_goals(db: DepDb, user: DepUser) -> list[GoalResponse]:
    return list(crud.get_goals(db, cast(int, user.id)))


@api.post("/goals")
def add_goal(db: DepDb, user: DepUser, goal: GoalCreate) -> list[GoalResponse]:
    crud.create_goal(db, cast(int, user.id), goal)
    return get_goals(db, user)


@api.patch("/goals/{goal_id}")
def update_goal(db: DepDb, user: DepUser, goal_id: int, goal: GoalUpdate) -> list[GoalResponse]:
    crud.update_goal(db, cast(int, user.id), goal_id, goal)
    return get_goals(db, user)


@api.delete("/goals/{gial_id}")
def delete_goal(db: DepDb, user: DepUser, goal_id: int):
    crud.delete_goal(db, cast(int, user.id), goal_id)
    return status.HTTP_200_OK


@api.get("/runs", response_model=list[RunResponse])
def get_runs(
    db: DepDb,
    user: DepUser,
    from_: Annotated[datetime, Query(alias="from")],
    to: datetime,
) -> list[Run]:
    return list(crud.get_runs(db, cast(int, user.id), from_, to))
