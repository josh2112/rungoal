from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.sse import EventSourceResponse
from jose import JWTError

from rungoal import auth, crud
from rungoal.deps import DepDb, DepSettings, DepUser
from rungoal.models import AccessToken, GoogleApiAuthCode, User, UserBase
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


@api.post("/auth/dev", tags=["Auth"])
async def dev_login(db: DepDb, settings: DepSettings, response: Response) -> AccessToken:
    # Returns the first user in the DB (dev only)
    if not settings.DEV:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = crud.get_user(db, 1)
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


@api.get("/user/me")
def get_user(user: DepUser) -> UserBase:
    return user  # Will return only the fields in UserBase


@api.get("/sync/status")
def get_sync_status(user: DepUser) -> SyncState:
    assert user.id is not None
    return sync_status(user.id)


@api.get("/sync/stream", response_class=EventSourceResponse)
async def get_sync_stream(user: DepUser) -> AsyncIterable[SyncState]:
    assert user.id is not None
    async for p in sync_stream(user.id):
        yield p


@api.post("/sync")
async def start_sync(user: DepUser, include_runtracker: bool = False):
    await sync_start(user, include_runtracker)
    return status.HTTP_202_ACCEPTED
