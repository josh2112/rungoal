import json
import threading
from collections.abc import Generator
from functools import cache

import google.auth.transport.requests
import httpx
from google.oauth2.credentials import Credentials
from sqlmodel import Session

from rungoal.models import User
from rungoal.utils import TimeRange


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


class GoogleHealthClient(httpx.Client):
    GOOGLE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, user: User, db: Session, *args, **kwargs):
        kwargs.setdefault("base_url", "https://health.googleapis.com/v4/users/me/dataTypes")
        kwargs["auth"] = _GoogleApiAuth(user, db)
        kwargs.setdefault("headers", {"Accept": "application/json"})
        super().__init__(*args, **kwargs)

    def fetch_runs(self, range_: TimeRange):
        field = "exercise.interval.civil_start_time"
        a = f'{field} >= "{range_.start.strftime(self.GOOGLE_DATETIME_FORMAT)}"'
        b = f'{field} < "{range_.end.strftime(self.GOOGLE_DATETIME_FORMAT)}"'
        response = self.get(
            "/exercise/dataPoints:reconcile",
            params={"filter": f"{a} AND {b}"},
        )
        response.raise_for_status()

        content = response.json()
        return (
            [dp for dp in content["dataPoints"] if dp["exercise"]["exerciseType"] == "RUNNING"]
            if "dataPoints" in content
            else []
        )

    def fetch_tcx(self, exercise_id: str) -> bytes:
        response = self.get(
            f"/exercise/dataPoints/{exercise_id}:exportExerciseTcx?alt=media",
        )
        response.raise_for_status()
        return response.content
