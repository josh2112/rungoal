import json
import threading
from collections.abc import Generator, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import cache

import google.auth.transport.requests
import httpx
from google.oauth2.credentials import Credentials
from sqlmodel import Session

from rungoal.models import User


@cache
def _client_secret() -> tuple[str, str, str]:
    with open("client_secret.json") as f:
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


_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _datetime_chunk(
    from_: datetime, to: datetime, size: timedelta
) -> Iterator[tuple[datetime, datetime]]:
    cur = from_
    nxt = from_ + size
    while nxt < to:
        yield cur, nxt
        cur = nxt
        nxt += size
    yield cur, to


def _make_time_filter(field: str, range: tuple[datetime, datetime]) -> str:
    a = f'{field} >= "{range[0].strftime(_DATETIME_FORMAT)}"'
    b = f'{field} < "{range[1].strftime(_DATETIME_FORMAT)}"'
    return f"{a} AND {b}"


class GoogleHealthClient(httpx.Client):
    def __init__(self, user: User, db: Session, *args, **kwargs):
        kwargs.setdefault("base_url", "https://health.googleapis.com/v4/")
        kwargs["auth"] = _GoogleApiAuth(user, db)
        kwargs.setdefault("headers", {"Accept": "application/json"})
        super().__init__(*args, **kwargs)

    def fetch_runs(self, from_: datetime, to: datetime):
        def _fetch(range: tuple[datetime, datetime]):
            response = self.get(
                "/users/me/dataTypes/exercise/dataPoints:reconcile",
                params={"filter": _make_time_filter("exercise.interval.civil_start_time", range)},
            )
            response.raise_for_status()
            return response.json()

        with ThreadPoolExecutor() as executor:
            results = executor.map(_fetch, list(_datetime_chunk(from_, to, timedelta(days=10))))
            return [
                dp
                for r in results
                for dp in r["dataPoints"]
                if dp["exercise"]["exerciseType"] == "RUNNING"
            ]

    def fetch_tcx(self, exercise_ids: [str]) -> Iterator[tuple[int, bytes]]:
        def _fetch(id: str):
            response = self.get(
                f"/users/me/dataTypes/exercise/dataPoints/{id}:exportExerciseTcx?alt=media",
            )
            response.raise_for_status()
            return id, response.content

        with ThreadPoolExecutor(max_workers=4) as executor:
            return executor.map(_fetch, exercise_ids)

    def fetch_heart_rates(self, from_: datetime, to: datetime):
        response = self.get(
            "/users/me/dataTypes/heart-rate/dataPoints:reconcile",
            params={
                "filter": _make_time_filter("heart_rate.sample_time.physical_time", (from_, to))
            },
        )
        response.raise_for_status()
        return response.json()
