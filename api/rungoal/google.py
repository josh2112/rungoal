import json
import threading
import xml.etree.ElementTree as ET
from collections.abc import Generator
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import cast

import google.auth.transport.requests
import httpx
from google.oauth2.credentials import Credentials
from sqlmodel import Session

from .models import (
    DeviceType,
    RecordingMethod,
    RecordingPlatform,
    Run,
    RunDataSource,
    RunFetchContext,
    TrackPoint,
    User,
)
from .utils import TimeRange


@cache
def _client_secret() -> tuple[str, str, str]:
    with open("../client_secret.json") as f:
        contents = json.load(f)["web"]
        return contents["client_id"], contents["client_secret"], contents["token_uri"]


class _GoogleApiAuth(httpx.Auth):
    def __init__(self, user: User, db: Session):
        client_id, client_secret, token_uri = _client_secret()
        self.user, self.db = user, db
        self.creds = Credentials(
            token=user.google_api_access_token,
            refresh_token=user.google_api_refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri=token_uri,
        )
        self.lock = threading.Lock()

    def _refresh_token(self):
        # This should only ever be called ONCE per thread pool. The first request that fails with an
        # expired token will refresh it; all other requests will wait on the lock.
        self.creds.refresh(google.auth.transport.requests.Request())
        self.user.google_api_access_token = self.creds.token
        self.db.add(self.user)
        self.db.commit()

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.creds.token}"
        response = yield request

        if response.status_code == 401:
            with self.lock:
                # Ensure nothing else in the thread pool has already refreshed the token before
                # doing it ourselves
                if request.headers["Authorization"].split(" ")[1] == self.creds.token:
                    self._refresh_token()
                request.headers["Authorization"] = f"Bearer {self.creds.token}"
            yield request


class GoogleHealthClient(httpx.Client):
    FILTER_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, user: User, db: Session, *args, **kwargs):
        self.db, self.user = db, user
        kwargs.setdefault("base_url", "https://health.googleapis.com/v4/users/me/")
        kwargs["auth"] = _GoogleApiAuth(user, db)
        kwargs.setdefault("headers", {"Accept": "application/json"})
        kwargs.setdefault("transport", httpx.HTTPTransport(retries=10))
        kwargs.setdefault("timeout", httpx.Timeout(10.0, connect=5.0))
        super().__init__(*args, **kwargs)

    def fetch_runs(
        self, range_: TimeRange, time_zones_accounted_for: bool = False, output: Path | None = None
    ) -> list[Run]:
        field = "exercise.interval.civil_start_time"

        # civil_start_time is in local time. Since we don't know what time zone these potential runs are in,
        # subtract a day (unless the user has already done that and set [time_zones_accounted_for].)
        if not time_zones_accounted_for:
            range_.start -= timedelta(days=1)

        a = f'{field} >= "{range_.start.strftime(self.FILTER_DATETIME_FORMAT)}"'
        b = f'{field} < "{range_.end.strftime(self.FILTER_DATETIME_FORMAT)}"'

        response = self.get(
            "dataTypes/exercise/dataPoints",
            params={"filter": f"{a} AND {b}"},
        )
        response.raise_for_status()

        content = response.json()

        return (
            [
                self._run_from_data_point(dp, output)
                for dp in content["dataPoints"]
                if dp["exercise"]["exerciseType"] == "RUNNING"
            ]
            if "dataPoints" in content
            else []
        )

    def fetch_tcx(self, run: RunFetchContext, output: Path | None = None) -> list[TrackPoint]:
        response = self.get(
            f"dataTypes/exercise/dataPoints/{run.data_source_id}:exportExerciseTcx?alt=media",
        )
        response.raise_for_status()

        if output:
            with open((output / run.data_source_id).with_suffix(".tcx"), "wb") as f:
                f.write(response.content)

        ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
        root = ET.fromstring(response.content)
        trackpoints = []

        def get_subel_text(el: ET.Element, name: str) -> str | None:
            text = subel.text if (subel := el.find(f"./tcx:{name}", ns)) is not None else None
            return text or None

        def get_subel_float(el: ET.Element, name: str) -> float | None:
            return float(v) if (v := get_subel_text(el, name)) else None

        def get_subel_int(el: ET.Element, name: str) -> int | None:
            return int(v) if (v := get_subel_text(el, name)) else None

        nodes = root.findall(".//tcx:Trackpoint", ns)
        start_time = datetime.fromisoformat(cast(str, get_subel_text(nodes[0], "Time")))

        for tp in nodes:
            trackpoints.append(
                TrackPoint(
                    run_id=run.id,
                    elapsed_secs=(
                        datetime.fromisoformat(cast(str, get_subel_text(tp, "Time"))) - start_time
                    ).total_seconds(),
                    alt_meters=get_subel_float(tp, "AltitudeMeters"),
                    distance_meters=get_subel_float(tp, "DistanceMeters"),
                    lat_deg=get_subel_float(tp, "Position/tcx:LatitudeDegrees"),
                    lon_deg=get_subel_float(tp, "Position/tcx:LongitudeDegrees"),
                    heart_rate_bpm=get_subel_int(tp, "HeartRateBpm/tcx:Value"),
                )
            )

        return trackpoints

    def _run_from_data_point(self, dp: dict, output: Path | None = None) -> Run:
        data_source_id = dp["name"].split("/")[-1]
        ex = dp["exercise"]
        metrics = ex["metricsSummary"]
        mobMet = metrics.get("mobilityMetrics", {})
        ds = dp["dataSource"]

        if output:
            with open((output / data_source_id).with_suffix(".json"), "w") as f:
                json.dump(dp, f, indent=True)

        return Run(
            user_id=self.user.id,
            data_source=RunDataSource.GOOGLE_HEALTH,
            data_source_id=data_source_id,
            start_time=datetime.fromisoformat(ex["interval"]["startTime"]),
            end_time=datetime.fromisoformat(ex["interval"]["endTime"]),
            utc_offset_seconds=int(ex["interval"]["startUtcOffset"][:-1]),
            update_time=datetime.fromisoformat(ex["updateTime"]),
            calories=metrics.get("caloriesKcal"),
            distance_millimeters=metrics["distanceMillimeters"],
            average_pace_seconds_per_meter=metrics["averagePaceSecondsPerMeter"],
            steps=int(tmp) if (tmp := metrics.get("steps")) else None,
            elevation_gain_millimeters=metrics.get("elevationGainMillimeters"),
            active_duration=float(ex["activeDuration"][:-1]),
            avg_cadence_steps_per_minute=mobMet.get("avgCadenceStepsPerMinute"),
            avg_stride_length_millimeters=mobMet.get("avgStrideLengthMillimeters"),
            avg_vertical_oscillation_millimeters=mobMet.get("avgVerticalOscillationMillimeters"),
            avg_vertical_ratio=mobMet.get("avgVerticalRatio"),
            platform=next((rp for rp in RecordingPlatform if rp == ds["platform"]), None),
            recording_method=next(
                (rm for rm in RecordingMethod if rm == ds["recordingMethod"]), None
            ),
            device_type=next(
                (dt for dt in DeviceType if dt == ds.get("device", {}).get("formFactor")), None
            ),
            device_name=ds.get("device", {}).get("displayName"),
            avg_ground_contact_time_duration=float(tmp[:-1])
            if (tmp := mobMet.get("avgGroundContactTimeDuration"))
            else None,
        )
