import contextlib
import json
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, track
from sqlmodel import select

from rungoal.crud import get_user
from rungoal.deps import dep_db, dep_db_engine
from rungoal.google import GoogleHealthClient
from rungoal.models import User
from rungoal.settings import settings


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
def fetch_runs(
    user_id: int,
    from_: datetime,
    output: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            writable=True,
            resolve_path=True,
        ),
    ],
    to: datetime = None,
):
    from_ = from_.replace(tzinfo=UTC)
    to = to.replace(tzinfo=UTC) if to else datetime.now(UTC)
    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            folder = output / "runs"
            folder.mkdir(parents=True, exist_ok=True)
            with Progress(SpinnerColumn(), TextColumn("Downloading runs..."), transient=True) as p:
                try:
                    for ex in client.fetch_runs(from_, to):
                        path = (folder / ex["dataPointName"].split("/")[-1]).with_suffix(".json")
                        with open(path, "w") as f:
                            json.dump(ex, f, indent=4)
                except httpx.HTTPStatusError as e:
                    traceback.print_exc()
                    print(f"Response data: {e.response.json()}")


@app.command()
def fetch_tcx(
    user_id: int,
    output: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            writable=True,
            resolve_path=True,
        ),
    ],
    from_runs_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    exercise_id: int = None,
):
    if not from_runs_path and not exercise_id:
        raise Exception("Either from-runs-path or exercise-id must be specified")
    ids = [exercise_id] if exercise_id else [f.stem for f in from_runs_path.glob("*.json")]
    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            folder = output / "tcx"
            folder.mkdir(parents=True, exist_ok=True)
            try:
                for ex_id, tcx in client.fetch_tcx(ids):
                    path = (folder / ex_id).with_suffix(".tcx")
                    with open(path, "wb") as f:
                        f.write(tcx)
            except httpx.HTTPStatusError as e:
                print(f"Error: {e.response.json()}")


@app.command()
def fetch_heart_rates(
    user_id: int,
    output: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            writable=True,
            resolve_path=True,
        ),
    ],
    from_runs_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    exercise_id: str = None,
):
    if not from_runs_path and not exercise_id:
        raise Exception("Either from-runs-path or exercise-id must be specified")
    exercise_ids = [exercise_id] if exercise_id else [f.stem for f in from_runs_path.glob("*.json")]
    folder = output / "heartRates"
    folder.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            for ex_id in track(exercise_ids):
                with open(Path(output / "runs" / ex_id).with_suffix(".json")) as f:
                    ex = json.load(f)
                    from_ = datetime.fromisoformat(ex["exercise"]["interval"]["startTime"])
                    to = datetime.fromisoformat(ex["exercise"]["interval"]["endTime"])
                    try:
                        path = (folder / ex_id).with_suffix(".json")
                        with open(path, "w") as f:
                            json.dump(client.fetch_heart_rates(from_, to), f, indent=4)
                    except httpx.HTTPStatusError as e:
                        print(f"Error: {e.response.json()}")
