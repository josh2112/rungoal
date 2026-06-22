from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Unicode
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from sqlmodel import AutoString, Field, SQLModel

from rungoal.settings import settings

# ========= Auth ========


class GoogleApiAuthCode(BaseModel):
    google_access_code: str


class AccessToken(BaseModel):
    access_token: str


# ========= DB ========


class UserBase(SQLModel):
    name: str
    email: EmailStr = Field(index=True, unique=True, sa_type=AutoString)
    avatar_uri: str


class UserWithGoogleCreds(UserBase):
    google_api_access_token: str
    google_api_refresh_token: str = Field(
        sa_column=Column(
            EncryptedType(Unicode, settings.GOOGLE_REFRESH_TOKEN_KEY, AesEngine, "pkcs5")
        )
    )


class User(UserWithGoogleCreds, table=True):
    id: int | None = Field(default=None, primary_key=True)


class Error(BaseModel):
    title: str
    detail: str | None = None
    source: str | None = None
