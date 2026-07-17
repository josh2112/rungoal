import contextlib
import os
from functools import cache
from typing import cast

from sqlalchemy import Engine, event, make_url
from sqlmodel import Session, create_engine

from alembic.config import Config
from rungoal.settings import settings


# For file-based DBs (like SQLite), ensure the directory exists
def ensure_db_path_exists( alembic_config: Config ):
    db_url = make_url(cast(str, alembic_config.get_main_option("sqlalchemy.url")))

    if db_url.drivername.startswith("sqlite") and db_url.database:
        if db_dir := os.path.dirname(db_url.database):
            os.makedirs(db_dir, exist_ok=True)


@cache
def get_engine() -> Engine:
    """Initialize the production database. Only called once!"""
    alembic_config = Config("alembic.ini")
    db_url = alembic_config.get_main_option("sqlalchemy.url")
    assert db_url

    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}, echo=settings.DEBUG_SQL
    )
    event.listen(engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys = ON"))

    return engine


@contextlib.contextmanager
def get_db():
    with Session(get_engine()) as session:
        yield session
