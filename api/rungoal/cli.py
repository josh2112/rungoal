import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.progress import Progress
from sqlmodel import Session, select

from rungoal.crud import get_user
from rungoal.database import get_engine
from rungoal.google import GoogleHealthClient, datetime_chunk
from rungoal.models import User

app = typer.Typer()


@contextlib.contextmanager
def get_db():
    with Session(get_engine()) as session:
        yield session


WritableFolderOpt = typer.Argument(
    file_okay=False,
    writable=True,
    resolve_path=True,
)

RunsFolderOpt = typer.Argument(
    file_okay=False,
    resolve_path=True,
)


@app.command()
def users():
    with get_db() as db:
        for user in db.exec(select(User)).all():
            print(f"{user.id}, {user.name}, {user.email}")


@app.command()
def fetch_runs(
    user_id: int,
    from_: datetime,
    output: Annotated[Path, WritableFolderOpt],
    to: datetime | None = None,
):
    # Only grab at most 10 days of data at a time to avoid this Google Health API v4 bug:
    # https://issuetracker.google.com/issues/510170708
    # If a run is too far down in the list of returned results, it may have run-specific data
    # stripped off and report as a regular exercise.
    ranges = list(
        datetime_chunk(
            from_.replace(tzinfo=UTC),
            to.replace(tzinfo=UTC) if to else datetime.now(UTC),
            timedelta(days=10),
        )
    )

    folder = output / "runs"
    folder.mkdir(parents=True, exist_ok=True)

    with get_db() as db, Progress() as p:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:

            def _fetch(range_: tuple[datetime, datetime]):
                dataPoints = client.fetch_runs(range_)
                for ex in dataPoints:
                    path = (folder / ex["dataPointName"].split("/")[-1]).with_suffix(".json")
                    with open(path, "w") as f:
                        json.dump(ex, f, indent=4)
                p.update(t1, advance=1)

            t1 = p.add_task("Downloading runs...", total=len(ranges))
            try:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    return list(executor.map(_fetch, ranges))
            except httpx.HTTPStatusError as e:
                print(f"Error: {e.response.json()}")


@app.command()
def fetch_tcx(
    user_id: int,
    output: Annotated[Path, WritableFolderOpt],
    from_runs_path: Annotated[Path | None, RunsFolderOpt] = None,
    exercise_id: str | None = None,
):
    if exercise_id:
        ids = [exercise_id]
    elif from_runs_path:
        ids = [f.stem for f in from_runs_path.glob("*.json")]
    else:
        raise Exception("Either from-runs-path or exercise-id must be specified")

    folder = output / "tcx"
    folder.mkdir(parents=True, exist_ok=True)

    with get_db() as db, Progress() as p:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:

            def _fetch(id_: str):
                tcx = client.fetch_tcx(id_)
                path = (folder / id).with_suffix(".tcx")
                with open(path, "wb") as f:
                    f.write(tcx)
                p.update(t1, advance=1)

            t1 = p.add_task("Downloading TCX files...", total=len(ids))
            try:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    return list(executor.map(_fetch, ids))
            except httpx.HTTPStatusError as e:
                print(f"Error: {e.response.json()}")
