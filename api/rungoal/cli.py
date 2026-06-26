import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from rungoal.crud import get_user
from rungoal.database import get_engine
from rungoal.google import GoogleHealthClient
from rungoal.models import Run, RunDataSource, User
from rungoal.utils import TimeRange

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
def fetch_all_runs(user_id: int, output: Annotated[Path, WritableFolderOpt]):
    # Syncs all GH API runs. We can't just do one massive query and page it due to GH API bugs (runs
    # at the bottom of large queries may not include run-specific data), instead we can only query
    # about 10 days at a time. So do a binary search to find the very first recorded run (with a
    # lower bound of Jan 1 2020), then fetch from there.

    folder = output / "runs"
    folder.mkdir(parents=True, exist_ok=True)

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
    output: Annotated[Path, WritableFolderOpt],
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
                path = (folder / id_).with_suffix(".tcx")
                with open(path, "wb") as f:
                    f.write(tcx)
                p.update(t1)

            t1 = p.add_task("Downloading TCX files...", total=len(ids))
            try:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    return list(executor.map(_fetch, ids))
            except httpx.HTTPStatusError as e:
                print(f"Error: {e.response.json()}")


@app.command()
def sync_runtracker(user_id: int, runs_path: Annotated[Path, RunsFolderOpt]):
    # Sync runs from the RunTracker app to our local DB. This assumes that all GH runs
    # have already been downloaded.
    from rungoal.import_runtracker import RuntrackerRunSession, RuntrackerUser, get_runtracker_db

    gh_runs = []
    for path in runs_path.glob("*.json"):
        with open(path) as f:
            gh_runs.append(json.load(f))

    gh_runs_by_date = {
        datetime.fromisoformat(r["exercise"]["interval"]["startTime"]).date(): r for r in gh_runs
    }

    with get_db() as db:
        user_email = get_user(db, user_id).email

    with get_runtracker_db() as db:
        user = db.exec(select(RuntrackerUser).where(RuntrackerUser.email == user_email)).first()
        if not user:
            print(f"No user with email '{user_email}' found in RunTracker database.")
            return

        for rt_run in db.exec(
            select(RuntrackerRunSession).where(RuntrackerRunSession.user_id == user.id)
        ):
            if gh_run := gh_runs_by_date.get(rt_run.date):
                # We found a runtracker run matching a GH run by date. HealthConnect apparently
                # doesn't sync calories from SamsungHealth, so import them here. But we ADD to
                # EXISTING calories in case there are multiple runs on this date.
                if "caloriesKcal" not in gh_run["exrcise"]["metricsSummary"]:
                    gh_run["exrcise"]["metricsSummary"]["caloriesKcal"] = rt_run.calories
                else:
                    gh_run["exrcise"]["metricsSummary"]["caloriesKcal"] += rt_run.calories


@app.command()
def import_runs(user_id: int, runs_path: Annotated[Path, RunsFolderOpt]):
    # Import the JSON run data into the database
    with get_db() as db:
        user = get_user(db, user_id)

        for p in runs_path.glob("*.json"):
            with open(p) as f:
                content = json.load(f)
            ex = content["exercise"]
            metrics = ex["metricsSummary"]
            mobMet = metrics.get("mobilityMetrics")

            try:
                db.add(
                    Run(
                        user_id=user.id,
                        data_source=RunDataSource.GOOGLE_HEALTH,
                        start_time=datetime.fromisoformat(ex["interval"]["startTime"]),
                        end_time=datetime.fromisoformat(ex["interval"]["endTime"]),
                        calories=metrics.get("caloriesKcal"),
                        distance_millimeters=metrics["distanceMillimeters"],
                        average_pace_seconds_per_meter=metrics["averagePaceSecondsPerMeter"],
                        steps=int(metrics["steps"]) if "steps" in metrics else None,
                        elevation_gain_millimeters=metrics.get("elevationGainMillimeters"),
                        active_duration=float(ex["activeDuration"][:-1]),
                        avg_cadence_steps_per_minute=mobMet["avgCadenceStepsPerMinute"]
                        if mobMet
                        else None,
                        avg_stride_length_millimeters=mobMet["avgStrideLengthMillimeters"]
                        if mobMet
                        else None,
                        avg_vertical_oscillation_millimeters=mobMet[
                            "avgVerticalOscillationMillimeters"
                        ]
                        if mobMet
                        else None,
                        avg_vertical_ratio=mobMet["avgVerticalRatio"] if mobMet else None,
                        avg_ground_contact_time_duration=float(
                            mobMet["avgGroundContactTimeDuration"][:-1]
                        )
                        if mobMet
                        else None,
                    )
                )
            except Exception as e:
                e.add_note(f"dataPoint={p.stem}")
                raise

        db.commit()


@app.command()
def import_tcx(user_id: int, tcx_path: Annotated[Path, RunsFolderOpt]):
    import xml.etree.ElementTree as ET

    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}

    def get_subel_text(el: ET.Element, name: str):
        if (subel := el.find(f"./tcx:{name}", ns)) is not None:
            return subel.text
        return None

    for p in tcx_path.glob("*.tcx"):
        root = ET.parse(p).getroot()
        for tp in root.findall(".//tcx:Trackpoint", ns):
            if time := get_subel_text(tp, "Time"):
                print(datetime.fromisoformat(time))
            if alt := get_subel_text(tp, "AltitudeMeters"):
                print(float(alt))
            # TODO: Continue


@app.command()
def test_db_create():
    # 2. Configure the Database Connection
    # We use an in-memory SQLite database for testing, which wipes clean when the script stops.
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
