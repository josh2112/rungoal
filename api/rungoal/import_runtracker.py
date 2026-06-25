import contextlib
from datetime import date

from sqlmodel import Field, Session, SQLModel, create_engine

from rungoal.settings import settings

_URL = (
    "sqlite:///tmp/runtracker.db"
    if settings.DEV
    else "sqlite:////var/www/protected/runtracker/api/runtracker.db"
)


class RuntrackerRunSession(SQLModel, table=True):
    __tablename__: str = "runsession"

    id: int = Field(primary_key=True)
    date: date
    duration_secs: int
    distance_meters: int
    calories: int | None
    user_id: int


class RuntrackerGoal(SQLModel, table=True):
    __tablename__: str = "goal"
    id: int = Field(primary_key=True)
    user_id: int
    start_date: date
    end_date: date
    distance_meters: int


class RuntrackerUser(SQLModel, table=True):
    __tablename__: str = "user"

    id: int
    email: str
    goals: list[RuntrackerGoal]


@contextlib.contextmanager
def get_runtracker_db():
    engine = create_engine(_URL, connect_args={"check_same_thread": False})
    with Session(engine) as session:
        yield session
