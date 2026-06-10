from datetime import datetime, timedelta

from jose import jwt

ALGORITHM = "HS256"


def _create_token(data: dict, lifetime: timedelta) -> str:
    data = data.copy()
    data["exp"] = datetime.now(datetime.UTC) + lifetime
    return jwt.encode(data, KEY, algorithm=ALGORITHM)
