from functools import cache
from typing import Annotated

from fastapi import Depends
from jose import JWTError
from sqlalchemy import Engine
from sqlmodel import Session

from rungoal import auth, crud

from .database import get_engine
from .models import RequestUser
from .settings import Settings, settings


@cache
def dep_settings() -> Settings:
    return settings


def dep_db(engine: Annotated[Engine, Depends(get_engine)]):
    with Session(engine) as session:
        yield session


DepSettings = Annotated[Settings, Depends(dep_settings)]
DepDb = Annotated[Session, Depends(dep_db)]


def _user_from_access_token(db: DepDb, access_token: auth.AccessToken):
    """Decodes the access token and returns the associated User."""
    user = crud.get_user_by_email(db, access_token.subject)
    if not user:
        raise JWTError("Access token invalid")
    return RequestUser(**user.model_dump(), timezone=access_token.timezone)


def dep_user(
    access_token: Annotated[auth.AccessToken, Depends(auth.dep_bearer_token)], db: DepDb
) -> RequestUser:
    return _user_from_access_token(db, access_token)


def dep_user_from_query_token(
    access_token: Annotated[auth.AccessToken, Depends(auth.dep_query_token)], db: DepDb
) -> RequestUser:
    return _user_from_access_token(db, access_token)


DepUser = Annotated[RequestUser, Depends(dep_user)]
DepUserFromQueryToken = Annotated[RequestUser, Depends(dep_user_from_query_token)]
