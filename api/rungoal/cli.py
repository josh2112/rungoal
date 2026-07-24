from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import typer
from rich.progress import Progress as RichProgress
from sqlmodel import col, select

from rungoal.crud import get_user
from rungoal.database import get_db
from rungoal.google import GoogleHealthClient
from rungoal.models import (
    Run,
    RunFetchContext,
    TrackPoint,
    Weather,
)
from rungoal.sync import sync_runs, sync_runtracker, sync_tcx, sync_wx
from rungoal.utils import ProgressProtocol

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
    tcx: Annotated[bool, typer.Option(help="Sync TCX files")] = True,
    wx: Annotated[bool, typer.Option(help="Sync weather")] = True,
):
    if runtracker_db_path and not runtracker_tz:
        raise Exception("Please supply a time zone for Runtracker imports")

    with get_db() as db:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client, CliProgress() as progress:
            zone = ZoneInfo(runtracker_tz) if runtracker_tz else None
            sync_runs(client, progress, from_, to, runtracker_db_path, zone, tcx, wx)


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
def cmd_sync_tcx(user_id: int, from_: datetime, to: datetime | None = None):
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
        runs = db.exec(sql.where(col(Run.id).notin_(select(TrackPoint.run_id)))).all()
        with GoogleHealthClient(user, db) as client:
            sync_tcx(client, progress, list(RunFetchContext.model_validate(r) for r in runs))


@app.command("sync-weather", help="Syncs weather data for runs in the given timespan.")
def cmd_sync_weather(user_id: int, from_: datetime, to: datetime | None = None):
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
        runs = db.exec(sql.where(col(Run.id).notin_(select(Weather.run_id)))).all()
        sync_wx(db, progress, list(RunFetchContext.model_validate(r) for r in runs))


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


@app.command("stats", help="Calculates stats for the last run")
def cmd_calc_stats(run_ids: int, time_division_secs: int):
    with get_db() as db:
        for run_id in (run_ids,):
            trackpoints = db.exec(
                select(TrackPoint)
                .where(TrackPoint.run_id == run_id)
                .order_by(col(TrackPoint.elapsed_secs))
            ).all()
            if not trackpoints:
                continue

            # Divide the trackpoints into X-second-long chunks
            markers, end_time = [], time_division_secs
            for i, tp in enumerate(trackpoints):
                if tp.elapsed_secs > end_time:
                    markers.append(i)
                    end_time += time_division_secs

            start = 0
            gad_total, dist_total = 0, 0
            for end in markers:
                gad_chunk, dist_chunk = 0, 0
                hr_chunk = 0
                for i in range(start + 1, end + 1):
                    # Distance
                    d = trackpoints[i].distance_meters - trackpoints[i - 1].distance_meters
                    # Grade (change in alt / change in distance)
                    g = (
                        0
                        if not d
                        else (trackpoints[i].alt_meters - trackpoints[i - 1].alt_meters) / d
                    )
                    g = min(0.5, max(-0.5, g))
                    # GAP Factor (using Minetti polynomial)
                    gf = (
                        (((43.166667 * g - 8.444444) * g - 12.027778) * g + 12.861111) * g
                        + 5.416667
                    ) * g + 1.0
                    # Grade-adjusted distance
                    gad = d * gf
                    dist_chunk += d
                    gad_chunk += gad
                    hr_chunk += trackpoints[i].heart_rate_bpm or 0

                gad_total += gad_chunk
                dist_total += dist_chunk

                time_chunk = trackpoints[end].elapsed_secs - trackpoints[start + 1].elapsed_secs
                ngs_chunk = gad_chunk / time_chunk

                hr_chunk /= end - start + 1
                eff_chunk = ngs_chunk / hr_chunk if hr_chunk else 0

                print(
                    f"  distance={dist_chunk}, GAD={gad_chunk}, delta={round((gad_chunk / dist_chunk - 1) * 100, 2)}%, "
                )

                start = end

            print(
                f"distance={dist_total}, GAD={gad_total}, delta={round((gad_total / dist_total - 1) * 100, 2)}%, "
            )


@app.command(
    "init-db", help="Deletes and recreates the database, optionally recreating revision data."
)
def cmd_init_db(regen: bool = False):
    from alembic.config import Config

    from alembic import command

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


if __name__ == "__main__":
    app()
