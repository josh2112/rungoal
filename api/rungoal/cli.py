import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, col, delete, select

from rungoal.crud import get_user
from rungoal.database import get_engine
from rungoal.google import GoogleHealthClient
from rungoal.import_runtracker import RuntrackerGoal
from rungoal.models import (
    Goal,
    Run,
    RunDataSource,
    RunTcxFetchContext,
    TrackPoint,
    User,
    run_unique_constriant_columns,
)
from rungoal.utils import TimeRange

app = typer.Typer()


@contextlib.contextmanager
def get_db():
    with Session(get_engine()) as session:
        yield session


@app.command(help="Prints the user list.")
def users():
    with get_db() as db:
        for user in db.exec(select(User)).all():
            print(f"{user.id}, {user.name}, {user.email}")


@app.command(help="Syncs all known runs from Google Health to the database.")
def sync_all_runs(user_id: int):
    # Syncs all GH API runs. We can't just do one massive query and page it due to GH API bugs (runs
    # at the bottom of large queries may not include run-specific data), instead we can only query
    # about 10 days at a time. So do a binary search to find the very first recorded run (with a
    # lower bound of Jan 1 2020), then fetch from there.
    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                SpinnerColumn(),
                TextColumn("{task.fields[dates]}"),
            ) as progress:
                # First do a binary search.
                task = progress.add_task("Finding oldest runs...", dates="")
                d = timedelta(days=10)
                lower = TimeRange(datetime(year=2020, month=1, day=1, tzinfo=UTC), duration=d)
                upper = TimeRange(datetime.now(UTC) - d, duration=d)
                mid = TimeRange(lower.start + (upper.start - lower.start) / 2, duration=d)
                while not lower.overlaps(upper):
                    if client.fetch_runs(mid):
                        upper = mid
                    else:
                        lower = mid
                    mid = TimeRange(lower.start + (upper.start - lower.start) / 2, duration=d)
                    progress.update(task, advance=1, dates=mid.start.date().strftime("%Y-%m-%d"))

            with Progress() as progress:
                _sync_runs(client, lower.start, progress=progress)


@app.command(help="Syncs runs from Google Health to the database for the given time range.")
def sync_runs(user_id: int, from_: datetime, to: datetime | None = None):
    with Progress() as p, get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            _sync_runs(client, from_, to, p)


@app.command(help="Syncs runs from a Runtracker database (by email) to our database.")
def sync_runtracker(
    user_id: int, runtracker_db_path: Annotated[Path, typer.Argument(dir_okay=False, exists=True)]
):
    with get_db() as db, Progress() as progress:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            _sync_runtracker(client, runtracker_db_path, progress)


@app.command(help="Deletes and recreates the database, optionally recreating revision data.")
def init_db_test(regen: bool = False):
    from alembic import command
    from alembic.config import Config

    alembic_config = Config("alembic.ini")

    # Delete the DB
    if url := alembic_config.get_main_option("sqlalchemy.url"):
        Path(url.split("sqlite:///")[-1]).unlink(missing_ok=True)

    if regen:
        # Wipe all revisions and generate a new initial revision
        for p in Path("alembic/versions").glob("*.py"):
            p.unlink()

        command.revision(alembic_config, "Initial DB", True)

    # Create & upgrade the databse
    command.upgrade(alembic_config, "head")

    # Import a test user
    with get_db() as db, open("tmp/user.json") as f:
        db.add(User.model_validate(json.load(f)))
        db.commit()


########################################################################################################################


# Syncs runs from Google Health to the database for the given time range. Existing runs will only
# be overwritten in the event of a newer update time.
# Returns: List of new or updated runs
def _sync_runs(
    client: GoogleHealthClient,
    from_: datetime,
    to: datetime | None = None,
    progress: Progress | None = None,
):
    # Only grab at most 10 days of data at a time to avoid this Google Health API v4 bug:
    # https://issuetracker.google.com/issues/510170708
    # If a run is too far down in the list of returned results, it may have run-specific data
    # stripped off and report as a regular exercise.
    span = TimeRange(from_.replace(tzinfo=UTC), to.replace(tzinfo=UTC) if to else datetime.now(UTC))
    ranges = list(span.chunk(timedelta(days=10)))

    task = progress.add_task("Downloading runs...", total=len(ranges)) if progress else None

    def _fetch(range_: TimeRange):
        runs = client.fetch_runs(range_)
        if progress is not None and task is not None:
            progress.advance(task)
        return runs

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            runs = [run for lst in executor.map(_fetch, ranges) for run in lst]
    except httpx.HTTPStatusError as e:
        e.add_note(f"Response: {e.response.json()}")
        raise

    updated_runs = _update_runs(client.db, runs, span)
    _sync_tcx(client, updated_runs, progress)


# Syncs the given run list against existing runs over a timespan.
# 1) Existing runs with IDs not in the new runs are deleted.
# 2) New runs with IDs not in the existing runs are added.
# 3) Existing runs with a new run matching their ID are updated if the new run's update time
# is newer than the existing run's update time.
def _update_runs(db: Session, runs: list[Run], timespan: TimeRange) -> list[RunTcxFetchContext]:
    if not runs:
        return []

    db.exec(
        delete(Run)
        .where(col(Run.start_time) >= timespan.start)
        .where(col(Run.start_time) <= timespan.end)
        .where(col(Run.data_source_id).notin_([r.data_source_id for r in runs]))
    )
    db.commit()

    sql = insert(Run).values(
        # Get the runs as a Python dicts, values unmangled by JSON,
        # excluding ID.
        [
            {
                key: val
                for key, val in run.__dict__.items()
                if key in Run.model_fields and key != "id"
            }
            for run in runs
        ]
    )

    updated_runs = db.scalars(
        sql.on_conflict_do_update(
            index_elements=run_unique_constriant_columns,
            set_={
                n: getattr(sql.excluded, n)
                for n in Run.model_fields
                if n not in list(run_unique_constriant_columns) + ["id"]
            },
            where=sql.excluded.update_time > Run.update_time,
        ).returning(Run)
    ).all()
    db.commit()

    return list(RunTcxFetchContext.model_validate(r) for r in updated_runs)


def _sync_runtracker(
    client: GoogleHealthClient, runtracker_db_path: Path, progress: Progress | None = None
):
    from rungoal.import_runtracker import RuntrackerRunSession, RuntrackerUser, get_runtracker_db

    with get_runtracker_db(runtracker_db_path) as rt_db:
        rt_user = rt_db.exec(
            select(RuntrackerUser).where(RuntrackerUser.email == client.user.email)
        ).first()
        if not rt_user:
            print(f"No user with email '{client.user.email}' found in RunTracker database.")
            return

        gh_runs_by_date = {
            r.start_time.date(): r
            for r in client.db.exec(select(Run).where(Run.user_id == client.user.id)).all()
        }

        rt_runs = rt_db.exec(
            select(RuntrackerRunSession).where(RuntrackerRunSession.user_id == rt_user.id)
        ).all()

        task = (
            progress.add_task("Syncing Runtracker runs...", total=len(rt_runs))
            if progress
            else None
        )

        for rt_run in rt_runs:
            if run := gh_runs_by_date.get(rt_run.date):
                # We found a runtracker run matching a GH run by date. HealthConnect apparently
                # doesn't sync calories from SamsungHealth, so import them here. But we ADD to
                # EXISTING calories in case there are multiple runs on this date.
                # run.
                if run.calories is None:
                    run.calories = rt_run.calories
                elif rt_run.calories is not None:
                    run.calories += rt_run.calories
            else:
                # RunTracker runs only have a date (no time), so set them all to noon
                # in the local timezone
                start_utc = datetime.combine(rt_run.date, time(12, 0)).astimezone().astimezone(UTC)

                try:
                    end_time = start_utc + timedelta(seconds=rt_run.duration_secs)
                    run = Run(
                        user_id=client.user.id,
                        data_source=RunDataSource.RUNTRACKER,
                        data_source_id=str(rt_run.id),
                        start_time=start_utc,
                        end_time=end_time,
                        update_time=end_time,
                        calories=rt_run.calories,
                        distance_millimeters=rt_run.distance_meters * 1000,
                        average_pace_seconds_per_meter=rt_run.duration_secs
                        / rt_run.distance_meters,
                        active_duration=rt_run.duration_secs,
                        steps=None,
                        elevation_gain_millimeters=None,
                        avg_cadence_steps_per_minute=None,
                        avg_ground_contact_time_duration=None,
                        avg_stride_length_millimeters=None,
                        avg_vertical_oscillation_millimeters=None,
                        avg_vertical_ratio=None,
                    )

                except Exception as e:
                    e.add_note(f"RT run ID={rt_run.id}")
                    raise

            client.db.add(run)
            if progress is not None and task is not None:
                progress.advance(task)

        goals = client.db.exec(select(Goal).where(Goal.user_id == client.user.id))
        rt_goals = rt_db.exec(
            select(RuntrackerGoal).where(RuntrackerGoal.user_id == rt_user.id)
        ).all()

        task = (
            progress.add_task("Syncing Runtracker goals...", total=len(rt_goals))
            if progress
            else None
        )

        for rt_goal in rt_goals:
            match = next(
                (
                    g
                    for g in goals
                    if g.start_date == rt_goal.start_date
                    and g.start_date == rt_goal.end_date
                    and g.distance_meters == rt_goal.distance_meters
                ),
                None,
            )
            if not match:
                client.db.add(
                    Goal(
                        user_id=client.user.id,
                        start_date=rt_goal.start_date,
                        end_date=rt_goal.end_date,
                        distance_meters=rt_goal.distance_meters,
                    )
                )
            if progress is not None and task is not None:
                progress.advance(task)

        client.db.commit()


def _sync_tcx(
    client: GoogleHealthClient, runs: list[RunTcxFetchContext], progress: Progress | None = None
):
    task = progress.add_task("Downloading TCX files...", total=len(runs) + 1) if progress else None

    # Remove any trackpoints associated with these runs
    client.db.exec(delete(TrackPoint).where(col(TrackPoint.run_id).in_([r.id for r in runs])))
    client.db.commit()

    def _fetch(run: RunTcxFetchContext) -> list[TrackPoint]:
        # Sometimes the server hangs sending us a TCX file. Retry up to 4 times.
        retries = 4
        while True:
            try:
                trackpoints = client.fetch_tcx(run)
                if progress is not None and task is not None:
                    progress.advance(task)
                return trackpoints
            except httpx.ReadTimeout:
                if retries:
                    retries -= 1
                else:
                    raise

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            client.db.add_all(tp for lst in executor.map(_fetch, runs) for tp in lst)
        if progress is not None and task is not None:
            progress.advance(task)
    except httpx.HTTPStatusError as e:
        e.add_note(f"Response: {e.response.json()}")
        raise

    client.db.commit()
