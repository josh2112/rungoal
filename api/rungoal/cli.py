from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import typer
from rich.progress import Progress as RichProgress
from sqlalchemy import delete
from sqlmodel import col, select

from .crud import get_user
from .database import get_db
from .google import GoogleHealthClient
from .models import (
    Run,
    RunSplitStats,
    TrackPoint,
    Weather,
)
from .run_location import OverpassClient, sync_locations
from .sync import sync_runs, sync_runtracker, sync_split_stats, sync_tcx, sync_wx
from .utils import ProgressProtocol

app = typer.Typer()


class CliProgress(ProgressProtocol):
    def __init__(self):
        self.state = RichProgress()

    def start_task(self, task: str, total: float | None) -> None:
        self.state.add_task(task, total=total)

    def advance(self, task: str) -> None:
        t = next(t for t in self.state.tasks if t.description == task)
        self.state.advance(t.id)

    def complete_task(self, task: str) -> None:
        t = next(t for t in self.state.tasks if t.description == task)
        t.total = t.total if t.total else 1
        t.completed = t.total

    def __enter__(self):
        self.state.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.state.__exit__(exc_type, exc_value, traceback)


@app.command(
    "sync-runs",
    help="Syncs runs from Google Health to the database for the given time range. If 'from' is not "
    "given, syncs from the newest run (or all runs if none yet exist). If 'to' is not given, syncs "
    "to the current time. To pull in runs from an existing Runtracker database, provide the path."
    "To skip syncing TCX files or weather, use the --no-tcx or --no-wx flags.",
)
def cmd_sync_runs(
    user_id: int,
    from_: Annotated[
        datetime | None,
        typer.Option(
            "--from",
            help="Sync from this date. If not provided, syncs from the newest run, or if no runs,"
            "syncs from the oldest run found.",
        ),
    ] = None,
    to: Annotated[
        datetime | None,
        typer.Option(help="Sync to this date, or the current time if not provided."),
    ] = None,
    runtracker_db_path: Annotated[
        Path | None,
        typer.Option(dir_okay=False, exists=True, help="Sync runs from a Runtracker database"),
    ] = None,
    runtracker_tz: str | None = None,
    output: Annotated[
        Path | None,
        typer.Option(
            file_okay=False,
            help="If provided, downloaded files will be saved in this directory.",
        ),
    ] = None,
    tcx: Annotated[bool, typer.Option(help="Sync TCX files")] = True,
    wx: Annotated[bool, typer.Option(help="Sync weather")] = True,
    loc: Annotated[bool, typer.Option(help="Sync run locations")] = True,
):
    if runtracker_db_path and not runtracker_tz:
        raise ValueError("Please supply a time zone for Runtracker imports")

    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client, CliProgress() as progress:
            zone = ZoneInfo(runtracker_tz) if runtracker_tz else None
            sync_runs(client, progress, from_, to, runtracker_db_path, zone, output, tcx, wx, loc)


@app.command(
    "sync-runtracker", help="Syncs runs from a Runtracker database (by email) to our database."
)
def cmd_sync_runtracker(
    user_id: int,
    runtracker_db_path: Annotated[Path, typer.Argument(dir_okay=False, exists=True)],
    timezone: str,
):
    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client, CliProgress() as progress:
            sync_runtracker(client, progress, runtracker_db_path, ZoneInfo(timezone))


@app.command("sync-tcx", help="Syncs TCX track data for runs in the given timespan.")
def cmd_sync_tcx(
    user_id: int,
    from_: datetime,
    to: datetime | None = None,
    replace: bool = False,
    output: Annotated[
        Path | None,
        typer.Option(
            file_okay=False,
            help="If provided, downloaded .tcx data will be saved in this directory.",
        ),
    ] = None,
):
    with get_db() as db, CliProgress() as progress:
        user = get_user(db, user_id)
        # Select runs for this user and timespan for which we don't already have trackpoints
        sql = (
            select(Run)
            .where(Run.user_id == user.id)
            .where(Run.start_time >= from_.replace(tzinfo=UTC))
        )
        if to:
            sql = sql.where(Run.end_time <= to.replace(tzinfo=UTC))
        if not replace:
            sql = sql.where(col(Run.id).notin_(select(TrackPoint.run_id)))
        runs = db.exec(sql).all()
        with GoogleHealthClient(user, db) as client:
            sync_tcx(client, progress, runs, output)


@app.command("sync-weather", help="Syncs weather data for runs in the given timespan.")
def cmd_sync_weather(
    user_id: int, from_: datetime, to: datetime | None = None, replace: bool = False
):
    with get_db() as db, CliProgress() as progress:
        user = get_user(db, user_id)
        # Select runs for this user and timespan for which we don't already have weather
        sql = (
            select(Run)
            .where(Run.user_id == user.id)
            .where(Run.start_time >= from_.replace(tzinfo=UTC))
        )
        if to:
            sql = sql.where(Run.end_time <= to.replace(tzinfo=UTC))
        if not replace:
            sql = sql.where(col(Run.id).notin_(select(Weather.run_id)))
        runs = db.exec(sql).all()
        sync_wx(db, progress, runs)


@app.command("sync-split-stats", help="Syncs split stats for runs in the given timespan.")
def cmd_sync_split_stats(
    user_id: int,
    from_: datetime,
    to: datetime | None = None,
    replace: bool = False,
):
    with get_db() as db, CliProgress() as progress:
        user = get_user(db, user_id)
        # Select runs for this user and timespan for which we don't already have split stats
        sql = (
            select(Run)
            .where(Run.user_id == user.id)
            .where(Run.start_time >= from_.replace(tzinfo=UTC))
        )
        if to:
            sql = sql.where(Run.end_time <= to.replace(tzinfo=UTC))
        if not replace:
            sql = sql.where(col(Run.id).notin_(select(RunSplitStats.run_id)))
        runs = db.exec(sql).all()
        sync_split_stats(db, progress, runs)


@app.command("sync-locations", help="Syncs run locations for runs in the given timespan.")
def cmd_sync_locations(
    user_id: int, from_: datetime, to: datetime | None = None, replace: bool = False
):
    with get_db() as db, CliProgress() as progress, OverpassClient() as client:
        user = get_user(db, user_id)
        # Select runs for this user and timespan for which we don't already have location data
        sql = (
            select(Run)
            .where(Run.user_id == user.id)
            .where(Run.start_time >= from_.replace(tzinfo=UTC))
            .where(col(Run.track_points).any())
        )
        if to:
            sql = sql.where(Run.end_time <= to.replace(tzinfo=UTC))
        if not replace:
            sql = sql.where(col(Run.location_id).is_(None))
        runs = db.exec(sql).all()

        sync_locations(db, client, progress, runs)


@app.command(
    "del-recent-runs",
    help="Removes the most recent run(s) for the given user (helps debug syncing).",
)
def cmd_del_recent_runs(user_id: int, count: int = 1):
    with get_db() as db:
        user = get_user(db, user_id)
        runs = db.exec(
            select(Run)
            .where(Run.user_id == user.id)
            .order_by(col(Run.start_time).desc())
            .limit(count)
        ).all()
        for run in runs:
            db.delete(run)
        db.commit()


@dataclass
class IntRangeArgument:
    values: list[int]


""" 
def parse_int_range(value: str):
    return IntRangeArgument(
        [
            i
            for p in value.split(",")
            for a, _, b in [p.partition("-")]
            for i in range(int(a), int(b or a) + 1)
        ]
    )


import matplotlib.pyplot as plot


@app.command("plot-alt")
def cmd_plot_alt(run_ids: Annotated[IntRangeArgument, typer.Argument(parser=parse_int_range)]):
    with get_db() as db:
        for run_id in run_ids.values:
            trackpoints = db.exec(
                select(TrackPoint)
                .where(TrackPoint.run_id == run_id)
                .order_by(col(TrackPoint.elapsed_secs))
            ).all()
            x = [t.elapsed_secs for t in trackpoints]
            y = [t.alt_meters for t in trackpoints]
            plot.plot(x, y, label=str(run_id))
    plot.show() """


@app.command(
    "init-db", help="Deletes and recreates the database, optionally deleting revision scripts."
)
def cmd_init_db(
    regen: Annotated[
        bool,
        typer.Option(
            help="Delete all Alembic migration scripts and generate a single revision",
        ),
    ] = False,
):
    from alembic import command
    from alembic.config import Config

    alembic_config = Config("alembic.ini")

    # Delete the DB
    if url := alembic_config.get_main_option("sqlalchemy.url"):
        Path(url.split("sqlite:///")[-1]).unlink(missing_ok=True)

    if regen and typer.confirm("Regenerate revisions: Are you sure?"):
        # Wipe all revisions and generate a new initial revision
        for p in Path("alembic/versions").glob("*.py"):
            p.unlink()

        command.revision(alembic_config, "Initial DB", True)

    # Create & upgrade the databse
    command.upgrade(alembic_config, "head")


@app.command("reset-user")
def reset_user(user_id: int):
    with get_db() as db:
        db.exec(delete(Run).where(col(Run.user_id) == user_id))
        user = get_user(db, 1)
        user.is_onboarded = False
        db.add(user)
        db.commit()


@app.command("try-settings")
def cmd_try_settings(user_id: int):
    with get_db() as db:
        user = get_user(db, 1)
        with GoogleHealthClient(user, db) as client:
            client.update_user_settings()


if __name__ == "__main__":
    app()
