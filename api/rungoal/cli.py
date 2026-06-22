import asyncio
import contextlib
from functools import wraps

import typer
from sqlmodel import select

from rungoal.crud import get_user
from rungoal.deps import dep_db, dep_db_engine
from rungoal.google import fetch_recent_exercises
from rungoal.models import User
from rungoal.settings import settings


def async_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@contextlib.contextmanager
def get_db():
    return dep_db(dep_db_engine(settings))  # type: ignore


app = typer.Typer()


@app.command()
def users():
    with get_db() as db:
        for user in db.exec(select(User)).all():
            print(f"{user.id}, {user.name}, {user.email}")


@app.command()
@async_command
async def test_get_runs(user_id: int):
    with get_db() as db:
        user = get_user(db, user_id)
        print(await fetch_recent_exercises(user, db))


@app.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")
