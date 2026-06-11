from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError

from rungoal import auth, crud
from rungoal.deps import DepDb, DepSettings, DepUser
from rungoal.models import Authentication, GoogleApiAuthCode, User, UserBase

api = APIRouter(prefix="/api")


used_refresh_tokens = auth.UsedRefreshTokens()


@api.post("/auth/google")
def google_auth(auth_code: GoogleApiAuthCode, db: DepDb) -> Authentication:
    # Get full user info with Google API tokens
    google_user = auth.get_google_user(auth_code)
    user = crud.get_user_by_email(db, google_user.email)
    if user:
        # Update the existing user with the latest data (keeping the existing ID)
        db.add(User(id=user.id, **google_user.model_dump()))
        db.commit()
    else:
        user = crud.create_user(db, google_user)
    return auth.generate_token_pair(user.email)


@api.get("/auth/dev")
async def dev_login(db: DepDb, settings: DepSettings) -> Authentication:
    # Returns the first user in the DB (dev only)
    if not settings.DEV:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = crud.get_user(db, 1)
    return auth.generate_token_pair(user.email)


@api.post("/auth/refresh", tags=["Auth"])
def refresh_token(
    form: Annotated[auth.OAuth2RefreshRequestForm, Depends()], db: DepDb
) -> Authentication:
    # Will throw an exception if the refresh token has already been used
    used_refresh_tokens.add(form.refresh_token_encoded, form.refresh_token.expires)

    user = crud.get_user_by_email(db, form.refresh_token.subject)
    if not user:
        raise JWTError("Refresh token invalid")
    return auth.generate_token_pair(user.email)


@api.get("/user/me")
def get_user(user: DepUser) -> UserBase:
    return user
