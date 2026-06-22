from functools import cache
from typing import Annotated

from fastapi import Depends
from jose import JWTError
from sqlalchemy import Engine
from sqlmodel import Session

from rungoal import auth, crud
from rungoal.database import init_db
from rungoal.models import User
from rungoal.settings import settings, Settings


@cache
def dep_settings():
    """Returns a new settings object. Only called once!"""
    return settings


DepSettings = Annotated[Settings, Depends(dep_settings)]


@cache
def dep_db_engine(settings: DepSettings) -> Engine:
    """Initialize the production database. Only called once!"""
    return init_db(settings.DEBUG_SQL)


def dep_db(engine: Annotated[Engine, Depends(dep_db_engine)]):
    with Session(engine) as session:
        yield session


DepDb = Annotated[Session, Depends(dep_db)]


def dep_user(
    access_token: Annotated[auth.Token, Depends(auth.dep_bearer_token)], db: DepDb
) -> User:
    """Decodes the access token (from the Authorization header) and returns the associated User."""
    user = crud.get_user_by_email(db, access_token.subject)
    if not user:
        raise JWTError("Access token invalid")
    return user


DepUser = Annotated[User, Depends(dep_user)]
