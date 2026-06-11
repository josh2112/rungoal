from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, event
from sqlmodel import create_engine


def init_db(echo: bool = False) -> Engine:
    alembic_config = Config("alembic.ini")
    db_url = alembic_config.get_main_option("sqlalchemy.url")
    assert db_url

    engine = create_engine(db_url, connect_args={"check_same_thread": False}, echo=echo)
    event.listen(engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys = ON"))

    """Creates the DB or upgrades it to the latest version. Essentially 'alembic upgrade head'."""
    command.upgrade(alembic_config, "head")

    return engine
