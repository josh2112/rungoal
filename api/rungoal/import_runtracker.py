import contextlib
from datetime import date
from pathlib import Path

from sqlalchemy.orm import registry
from sqlmodel import Field, Session, SQLModel, create_engine

_runtracker_registry = registry()


class RuntrackerSQLModel(SQLModel, registry=_runtracker_registry):
    pass


class RuntrackerRunSession(RuntrackerSQLModel, table=True):
    __tablename__: str = "runsession"

    id: int = Field(primary_key=True)
    date: date
    duration_secs: int
    distance_meters: int
    calories: int | None
    user_id: int


class RuntrackerGoal(RuntrackerSQLModel, table=True):
    __tablename__: str = "goal"
    id: int = Field(primary_key=True)
    user_id: int
    start_date: date
    end_date: date
    distance_meters: int


class RuntrackerUser(RuntrackerSQLModel, table=True):
    __tablename__: str = "user"

    id: int = Field(primary_key=True)
    email: str


@contextlib.contextmanager
def get_runtracker_db(path: Path):
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    with Session(engine) as session:
        yield session
