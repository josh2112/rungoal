import json
from collections.abc import Generator
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


def credentials(token: str, refresh_token: str) -> Credentials:
    client_id, client_secret, token_uri = _client_secret()
    return Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
    )


class AsyncTokenAuth(httpx.Auth):
    def __init__(self, user: User, db: Session):
        self.user, self.db = user, db
        client_id, client_secret, token_uri = _client_secret()
        self.creds = Credentials(
            token=user.google_api_access_token,
            refresh_token=user.google_api_refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
        )

    def _refresh_token(self):
        self.creds.refresh(google.auth.transport.requests.Request())
        self.user.google_api_access_token = self.creds.token
        self.db.commit()
        # ---> IMPORTANT: Save `creds.token` to your database here so you have the fresh one! <---

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.creds.token}"

        response = yield request

        if response.status_code == 401:
            self._refresh_token()
            request.headers["Authorization"] = f"Bearer {self.creds.token}"
            yield request


class GoogleHealthClient(httpx.AsyncClient):
    def __init__(self, user: User, db: Session, *args, **kwargs):
        kwargs.setdefault("auth", AsyncTokenAuth(user, db))
        kwargs.setdefault(
            "headers",
            {
                "Accept": "application/json",
            },
        )

        super().__init__(*args, **kwargs)


async def fetch_recent_exercises(user: User, db: Session):
    async with GoogleHealthClient(user, db) as client:
        url = "https://health.googleapis.com/v4/users/me/dataTypes/exercise/dataPoints"

        # Example filter for the past week
        params = {}  # "filter": 'exercise.interval.start_time >= "2026-06-15T00:00:00Z"'}

        response = await client.get(url, params=params)

        response.raise_for_status()

        return response.json()
