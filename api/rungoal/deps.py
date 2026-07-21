from functools import cache
from typing import Annotated

from fastapi import Depends
from jose import JWTError
from sqlalchemy import Engine
from sqlmodel import Session

from rungoal import auth, crud
from rungoal.database import get_engine
from rungoal.models import RequestUser
from rungoal.settings import Settings, settings


@cache
def dep_settings() -> Settings:
    return settings


DepSettings = Annotated[Settings, Depends(dep_settings)]
_DepEngine = Annotated[Engine, Depends(get_engine)]


def dep_db(engine: _DepEngine):
    with Session(engine) as session:
        yield session


DepDb = Annotated[Session, Depends(dep_db)]


def dep_user(
    access_token: Annotated[auth.AccessToken, Depends(auth.dep_bearer_token)], db: DepDb
) -> RequestUser:
    """Decodes the access token (from the Authorization header) and returns the associated User."""
    user = crud.get_user_by_email(db, access_token.subject)
    if not user:
        raise JWTError("Access token invalid")
    return RequestUser(**user.model_dump(), timezone=access_token.timezone)


DepUser = Annotated[RequestUser, Depends(dep_user)]
