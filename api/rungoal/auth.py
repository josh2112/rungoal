import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Form, HTTPException, status
from fastapi.requests import Request
from fastapi.security.utils import get_authorization_scheme_param
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from jose import JWTError, jwt

from rungoal.models import Authentication, GoogleApiAuthCode, UserWithGoogleCreds
from rungoal.settings import Settings

_settings = Settings.model_validate({})

_JWT_ALGORITHM = "HS256"
_JWT_ACCESS_TOKEN_EXPIRY_MINS = 30
_JWT_REFRESH_TOKEN_EXPIRY_MINS = 30 * 24 * 60

_GOOGLE_API_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
]


@dataclass
class Token:
    subject: str
    expires: datetime


def _token_encode(subject: str, expiry_mins: int, key: str) -> str:
    return jwt.encode(
        {
            "sub": subject,
            "exp": int((datetime.now(UTC) + timedelta(minutes=expiry_mins)).timestamp()),
        },
        key=key,
        algorithm=_JWT_ALGORITHM,
    )


def _token_decode(token: str, key: str) -> Token:
    fields = jwt.decode(token, key, algorithms=[_JWT_ALGORITHM])
    return Token(
        subject=fields["sub"],
        expires=datetime.fromtimestamp(fields["exp"], tz=UTC),
    )


def access_token_encode(subject: str) -> str:
    """Creates an access token."""
    return _token_encode(subject, _JWT_ACCESS_TOKEN_EXPIRY_MINS, _settings.JWT_ACCESS_TOKEN_KEY)


def refresh_token_encode(subject: str) -> str:
    """Creates a refresh token."""
    return _token_encode(subject, _JWT_REFRESH_TOKEN_EXPIRY_MINS, _settings.JWT_REFRESH_TOKEN_KEY)


def access_token_decode(token: str) -> Token:
    """Decodes an access token."""
    return _token_decode(token, _settings.JWT_ACCESS_TOKEN_KEY)


def refresh_token_decode(token: str) -> Token:
    """Decodes a refresh token."""
    return _token_decode(token, _settings.JWT_REFRESH_TOKEN_KEY)


async def dep_bearer_token(request: Request) -> Token | None:
    """A FastAPI dependency to extract & return the bearer authorization from
    a request"""
    authorization = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return access_token_decode(token)


class OAuth2RefreshRequestForm:
    """Token refresh request form"""

    def __init__(
        self,
        grant_type: str = Form(None, pattern="refresh_token"),
        refresh_token: str = Form(...),
    ):
        self.grant_type = grant_type
        self.refresh_token_encoded = refresh_token
        self.refresh_token = refresh_token_decode(refresh_token)


class UsedRefreshTokens:
    """Manages refresh tokens ensuring one-time use"""

    def __init__(self):
        self._tokens: dict[str, datetime] = {}

    def add(self, token: str, expires: datetime):
        """Marks a refresh token as used. If already used, throws an exception. Also
        cleans up expired tokens."""
        # Prune expired tokens
        now = datetime.now(UTC)
        for t in [t for t, exp in self._tokens.items() if exp <= now]:
            del self._tokens[t]

        # If token is in blacklist, raise an exception
        if token in self._tokens:
            raise JWTError("Refresh token invalid")

        # Otherwise, add it
        self._tokens[token] = expires


def get_google_user(auth: GoogleApiAuthCode) -> UserWithGoogleCreds:
    """Verifies the auth code, client id, client secret, and scopes with Google
    for access and refresh tokens."""
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        _GOOGLE_API_SCOPES,
        redirect_uri="postmessage",
    )

    flow.fetch_token(code=auth.code)

    user_info = build("oauth2", "v2", credentials=flow.credentials).userinfo().get().execute()

    # The picture URL has "=sXX-c" appended to it, where the XX is the size in
    # pixels. We'll remove that, and the frontend can get the picture in whatever
    # size it likes.
    return UserWithGoogleCreds(
        name=user_info.get("name"),
        email=user_info.get("email"),
        avatar_uri=re.sub(r"=s\d+-c$", "", user_info.get("picture")),
        google_api_access_token=flow.credentials.token,
        google_api_refresh_token=flow.credentials.refresh_token,
    )


def generate_token_pair(sub: str) -> Authentication:
    return Authentication(
        access_token=access_token_encode(sub), refresh_token=refresh_token_encode(sub)
    )
