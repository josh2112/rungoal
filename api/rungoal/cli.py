import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import Session, select

from rungoal.crud import get_user
from rungoal.database import get_engine
from rungoal.google import GoogleHealthClient
from rungoal.models import Run, RunDataSource, TrackPoint, User
from rungoal.utils import TimeRange

app = typer.Typer()


@contextlib.contextmanager
def get_db():
    with Session(get_engine()) as session:
        yield session


OutputPathOpt = typer.Argument(
    file_okay=False,
    writable=True,
    resolve_path=True,
)

RunsPathOpt = typer.Argument(
    file_okay=False,
    resolve_path=True,
)


@app.command()
def users():
    with get_db() as db:
        for user in db.exec(select(User)).all():
            print(f"{user.id}, {user.name}, {user.email}")


@app.command()
def fetch_all_runs(user_id: int, output: Annotated[Path, OutputPathOpt]):
    # Syncs all GH API runs. We can't just do one massive query and page it due to GH API bugs (runs
    # at the bottom of large queries may not include run-specific data), instead we can only query
    # about 10 days at a time. So do a binary search to find the very first recorded run (with a
    # lower bound of Jan 1 2020), then fetch from there.
    with (
        get_db() as db,
        Progress(
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn(),
            TextColumn("{task.fields[dates]}"),
        ) as p,
    ):
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:
            # First do a binary search.
            t1 = p.add_task("Finding oldest runs...", dates="")
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
                p.update(t1, advance=1, dates=mid.start.date().strftime("%Y-%m-%d"))

    print(f"Oldest run is in range {mid.start.date()} to {mid.end.date()}")
    fetch_runs(1, mid.start, output)


@app.command()
def fetch_runs(
    user_id: int,
    from_: datetime,
    output: Annotated[Path, OutputPathOpt],
    to: datetime | None = None,
):
    # Only grab at most 10 days of data at a time to avoid this Google Health API v4 bug:
    # https://issuetracker.google.com/issues/510170708
    # If a run is too far down in the list of returned results, it may have run-specific data
    # stripped off and report as a regular exercise.
    span = TimeRange(from_.replace(tzinfo=UTC), to.replace(tzinfo=UTC) if to else datetime.now(UTC))
    ranges = list(span.chunk(timedelta(days=10)))

    folder = output / "runs"
    folder.mkdir(parents=True, exist_ok=True)

    with get_db() as db, Progress() as p:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:

            def _fetch(range_: TimeRange):
                dataPoints = client.fetch_runs(range_)
                for ex in dataPoints:
                    path = (folder / ex["dataPointName"].split("/")[-1]).with_suffix(".json")
                    with open(path, "w") as f:
                        json.dump(ex, f, indent=4)
                p.update(t1)

            t1 = p.add_task("Downloading runs...", total=len(ranges))
            try:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    return list(executor.map(_fetch, ranges))
            except httpx.HTTPStatusError as e:
                e.add_note(f"Response: {e.response.json()}")
                raise


@app.command()
def fetch_tcx(
    user_id: int,
    output: Annotated[Path, OutputPathOpt],
    runs_path: Annotated[Path | None, RunsPathOpt] = None,
    exercise_id: str | None = None,
):
    if exercise_id:
        ids = [exercise_id]
    elif runs_path:
        ids = [f.stem for f in runs_path.glob("*.json")]
    else:
        raise Exception("Either runs-path or exercise-id must be specified")

    folder = output / "tcx"
    folder.mkdir(parents=True, exist_ok=True)

    with get_db() as db, Progress() as p:
        user = get_user(db, user_id)
        with GoogleHealthClient(user, db) as client:

            def _fetch(id_: str):
                tcx = client.fetch_tcx(id_)
                path = (folder / id_).with_suffix(".tcx")
                with open(path, "wb") as f:
                    f.write(tcx)
                p.update(t1)

            t1 = p.add_task("Downloading TCX files...", total=len(ids))
            try:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    return list(executor.map(_fetch, ids))
            except httpx.HTTPStatusError as e:
                e.add_note(f"Response: {e.response.json()}")
                raise


@app.command()
def sync_runtracker(
    user_id: int, runtracker_db_path: Annotated[Path, typer.Argument(dir_okay=False, exists=True)]
):
    # Sync runs from the RunTracker app to our local DB. This assumes that all GH runs
    # have already been downloaded.
    from rungoal.import_runtracker import RuntrackerRunSession, RuntrackerUser, get_runtracker_db

    with get_db() as db, get_runtracker_db(runtracker_db_path) as rt_db:
        email = get_user(db, user_id).email

        user = rt_db.exec(select(RuntrackerUser).where(RuntrackerUser.email == email)).first()
        if not user:
            print(f"No user with email '{email}' found in RunTracker database.")
            return

        gh_runs_by_date = {
            r.start_time.date(): r for r in db.exec(select(Run).where(Run.user_id == user.id)).all()
        }

        for rt_run in rt_db.exec(
            select(RuntrackerRunSession).where(RuntrackerRunSession.user_id == user.id)
        ):
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
                    db.add(
                        Run(
                            user_id=user.id,
                            data_source=RunDataSource.RUNTRACKER,
                            data_source_id=str(rt_run.id),
                            start_time=start_utc,
                            end_time=start_utc + timedelta(seconds=rt_run.duration_secs),
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
                    )
                except Exception as e:
                    e.add_note(f"RT run ID={rt_run.id}")
                    raise

        db.commit()


@app.command()
def import_runs(user_id: int, runs_path: Annotated[Path, RunsPathOpt]):
    # Import the JSON run data into the database
    with get_db() as db:
        user = get_user(db, user_id)

        for p in runs_path.glob("*.json"):
            with open(p) as f:
                root = json.load(f)
            ex = root["exercise"]
            metrics = ex["metricsSummary"]
            mobMet = metrics.get("mobilityMetrics") or {}

            try:
                db.add(
                    Run(
                        user_id=user.id,
                        data_source=RunDataSource.GOOGLE_HEALTH,
                        data_source_id=root["dataPointName"].split("/")[-1],
                        start_time=datetime.fromisoformat(ex["interval"]["startTime"]),
                        end_time=datetime.fromisoformat(ex["interval"]["endTime"]),
                        calories=metrics.get("caloriesKcal"),
                        distance_millimeters=metrics["distanceMillimeters"],
                        average_pace_seconds_per_meter=metrics["averagePaceSecondsPerMeter"],
                        steps=int(tmp) if (tmp := metrics.get("steps")) else None,
                        elevation_gain_millimeters=metrics.get("elevationGainMillimeters"),
                        active_duration=float(ex["activeDuration"][:-1]),
                        avg_cadence_steps_per_minute=mobMet.get("avgCadenceStepsPerMinute"),
                        avg_stride_length_millimeters=mobMet.get("avgStrideLengthMillimeters"),
                        avg_vertical_oscillation_millimeters=mobMet.get(
                            "avgVerticalOscillationMillimeters"
                        ),
                        avg_vertical_ratio=mobMet.get("avgVerticalRatio"),
                        avg_ground_contact_time_duration=float(tmp[:-1])
                        if (tmp := mobMet.get("avgGroundContactTimeDuration"))
                        else None,
                    )
                )
            except Exception as e:
                e.add_note(f"dataPoint={p.stem}")
                raise

        db.commit()


@app.command()
def import_tcx(user_id: int, tcx_path: Annotated[Path, RunsPathOpt]):
    import xml.etree.ElementTree as ET

    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}

    def get_subel_text(el: ET.Element, name: str):
        subel = el.find(f"./tcx:{name}", ns)
        assert subel is not None and subel.text
        return subel.text

    with get_db() as db:
        user = get_user(db, user_id)

        for p in tcx_path.glob("*.tcx"):
            try:
                run = db.exec(
                    select(Run)
                    .where(Run.user_id == user.id)
                    .where(Run.data_source == RunDataSource.GOOGLE_HEALTH)
                    .where(Run.data_source_id == p.stem)
                ).one()

                root = ET.parse(p).getroot()
                for tp in root.findall(".//tcx:Trackpoint", ns):
                    el_hr = tp.find("./tcx:HeartRateBpm/tcx:Value", ns)

                    hr = int(el_hr.text) if el_hr is not None and el_hr.text is not None else None
                    db.add(
                        TrackPoint(
                            run_id=run.id,
                            elapsed_secs=(
                                datetime.fromisoformat(get_subel_text(tp, "Time")) - run.start_time
                            ).total_seconds(),
                            alt_meters=float(get_subel_text(tp, "AltitudeMeters")),
                            distance_meters=float(get_subel_text(tp, "DistanceMeters")),
                            heart_rate_bpm=hr,
                            lat_deg=float(get_subel_text(tp, "Position/tcx:LatitudeDegrees")),
                            lon_deg=float(get_subel_text(tp, "Position/tcx:LongitudeDegrees")),
                        )
                    )
            except Exception as e:
                e.add_note(f"dataPointID={p.stem}")
                raise
        db.commit()


@app.command()
def init_db_test():
    from alembic import command
    from alembic.config import Config

    alembic_config = Config("alembic.ini")

    # Delete the DB and any revisions
    if url := alembic_config.get_main_option("sqlalchemy.url"):
        Path(url.split("sqlite:///")[-1]).unlink(missing_ok=True)
    for p in Path("alembic/versions").glob("*.py"):
        p.unlink()

    # Generate a new initial revision
    command.revision(alembic_config, "Initial DB", True)

    # Create & upgrade the databse
    command.upgrade(alembic_config, "head")

    # Import a test user
    with get_db() as db, open("tmp/user.json") as f:
        db.add(User.model_validate(json.load(f)))
        db.commit()
