from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, col, delete, select

from rungoal.google import GoogleHealthClient
from rungoal.import_runtracker import RuntrackerGoal
from rungoal.models import (
    Goal,
    Run,
    RunDataSource,
    RunFetchContext,
    TrackPoint,
    Weather,
    run_unique_constriant_columns,
)
from rungoal.open_meteo import OpenMeteoClient
from rungoal.utils import ProgressProtocol, TimeRange

# Only grab at most _RUN_FETCH_DAYS days of data at a time to avoid this Google Health API v4 bug:
# https://issuetracker.google.com/issues/510170708
# If a run is too far down in the list of returned results, it may have run-specific data stripped
# off and report as a regular exercise.
_RUN_FETCH_DAYS = timedelta(days=10)


# Syncs runs from Google Health to the database for the given time range. Existing runs will only
# be overwritten in the event of a newer update time.
# [from]: If provided, syncs runs from this time to [to]. If not provided, finds the newest run
# and syncs from there. If no runs exist, finds the oldest run on Google Health.
# [to] defaults to the current time.
# If [include_runtracker] is true, looks for a Runtracker account with matching email and syncs it.
# We also sync TCX track files and look up historical weather for each run (unless told not to)
# Syncs the given run list against existing runs over a timespan.
# 1) Existing runs with IDs not in the new runs are deleted.
# 2) New runs with IDs not in the existing runs are added.
# 3) Existing runs with a new run matching their ID are updated if the new run's update time
# is newer than the existing run's update time.
# Returns list of runs that were added or updated.
def sync_runs(
    client: GoogleHealthClient,
    progress: ProgressProtocol,
    from_: datetime | None = None,
    to: datetime | None = None,
    runtracker_db_path: Annotated[Path, typer.Argument(dir_okay=False, exists=True)] | None = None,
    tcx: bool = True,
    wx: bool = True,
) -> TimeRange:
    task1 = "Finding oldest runs..."
    task2 = "Downloading runs..."

    if not from_:
        # Try to sync from the newest run.
        newest_run = client.db.exec(
            select(Run).where(Run.user_id == client.user.id).order_by(col(Run.start_time).desc())
        ).first()
        if newest_run:
            from_ = newest_run.start_time
        else:
            # No runs? Do a binary search to find the very first recorded run (with a lower bound
            # of Jan 1 2020), then begin the sync from there.
            d = _RUN_FETCH_DAYS
            lower = TimeRange(datetime(year=2020, month=1, day=1, tzinfo=UTC), duration=d)
            upper = TimeRange(datetime.now(UTC) - d, duration=d)
            mid = TimeRange(lower.start + (upper.start - lower.start) / 2, duration=d)
            progress.start_task(task1, total=None)
            while not lower.overlaps(upper):
                if client.fetch_runs(mid):
                    upper = mid
                else:
                    lower = mid
                mid = TimeRange(lower.start + (upper.start - lower.start) / 2, duration=d)
                progress.advance(task1)
            progress.complete_task(task1)
            from_ = lower.start

    span = TimeRange(from_.replace(tzinfo=UTC), to.replace(tzinfo=UTC) if to else datetime.now(UTC))
    ranges = list(span.chunk(_RUN_FETCH_DAYS))

    progress.start_task(task2, total=len(ranges))

    def _fetch(range_: TimeRange):
        runs = client.fetch_runs(range_)
        progress.advance(task2)
        return runs

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            runs = [run for lst in executor.map(_fetch, ranges) for run in lst]
    except httpx.HTTPStatusError as e:
        e.add_note(f"Response: {e.response.json()}")
        raise

    updated_runs = _update_runs(client.db, runs, span)
    if tcx:
        sync_tcx(client, progress, updated_runs)
    if wx:
        sync_wx(client.db, progress, updated_runs)
    if runtracker_db_path:
        sync_runtracker(client, progress, runtracker_db_path)

    return span


# Syncs the given run list against existing runs over a timespan.
# 1) Existing runs with IDs not in the new runs are deleted.
# 2) New runs with IDs not in the existing runs are added.
# 3) Existing runs with a new run matching their ID are updated if the new run's update time
# is newer than the existing run's update time.
# Returns list of runs that were added or updated.
def _update_runs(db: Session, runs: list[Run], timespan: TimeRange) -> list[RunFetchContext]:
    if not runs:
        return []

    print("In update_runs: Timespan =", timespan)
    print("Runs received:")
    for r in runs:
        print("  ", r.start_time)

    # Delete existing runs during this timespan that do not appear in the new run list
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

    return list(RunFetchContext.model_validate(r) for r in updated_runs)


def sync_runtracker(
    client: GoogleHealthClient, progress: ProgressProtocol, runtracker_db_path: Path
):
    from rungoal.import_runtracker import RuntrackerRunSession, RuntrackerUser, get_runtracker_db

    task1 = "Syncing Runtracker runs..."
    task2 = "Syncing Runtracker goals..."

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

        progress.start_task(task1, total=len(rt_runs))

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
            progress.advance(task1)

        goals = client.db.exec(select(Goal).where(Goal.user_id == client.user.id))
        rt_goals = rt_db.exec(
            select(RuntrackerGoal).where(RuntrackerGoal.user_id == rt_user.id)
        ).all()

        progress.start_task(task2, total=len(rt_goals))

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
            progress.advance(task2)

        client.db.commit()


def sync_tcx(client: GoogleHealthClient, progress: ProgressProtocol, runs: list[RunFetchContext]):
    task = "Downloading TCX files..."
    progress.start_task(task, total=len(runs) + 1)

    # Remove any trackpoints associated with these runs
    client.db.exec(delete(TrackPoint).where(col(TrackPoint.run_id).in_([r.id for r in runs])))
    client.db.commit()

    def _fetch(run: RunFetchContext) -> list[TrackPoint]:
        trackpoints = client.fetch_tcx(run)
        progress.advance(task)
        return trackpoints

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            client.db.add_all(tp for lst in executor.map(_fetch, runs) for tp in lst)
        progress.advance(task)
    except httpx.HTTPStatusError as e:
        e.add_note(f"Response: {e.response.json()}")
        raise

    client.db.commit()


def sync_wx(db: Session, progress: ProgressProtocol, runs: list[RunFetchContext]):
    task = "Downloading weather..."
    progress.start_task(task, total=len(runs) + 1)

    with OpenMeteoClient() as client:
        for run in runs:
            # Get average lat/lon of trackpoints (if we have any!)
            lat, lon = db.exec(
                select(func.avg(TrackPoint.lat_deg), func.avg(TrackPoint.lon_deg)).where(
                    TrackPoint.run_id == run.id
                )
            ).one()

            if lat is not None:
                try:
                    wx = client.fetch_weather(lat, lon, run.start_time, run.end_time)
                except Exception as e:
                    e.add_note(
                        f"lat={lat} lon={lon} start_time={run.start_time} end_time={run.end_time}"
                    )
                    raise
                db.add(Weather(run_id=run.id, **wx.model_dump()))

            progress.advance(task)

        db.commit()

    progress.advance(task)
