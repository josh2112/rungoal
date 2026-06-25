from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Unicode
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from sqlmodel import AutoString, Field, Relationship, SQLModel
from sqlmodel import Enum as SQLEnum

from rungoal.settings import settings

# ========= Auth ========


class GoogleApiAuthCode(BaseModel):
    googleAccessCode: str


class AccessToken(BaseModel):
    accessToken: str


# ========= DB ========


class UserBase(SQLModel):
    name: str
    email: EmailStr = Field(index=True, unique=True, sa_type=AutoString)
    avatarUri: str


class UserWithGoogleCreds(UserBase):
    googleApiAccessToken: str
    googleApiRefreshToken: str = Field(
        sa_column=Column(
            EncryptedType(Unicode, settings.GOOGLE_REFRESH_TOKEN_KEY, AesEngine, "pkcs5")
        )
    )


class User(UserWithGoogleCreds, table=True):
    id: int | None = Field(default=None, primary_key=True)
    runs: list["Run"] = Relationship(back_populates="user", cascade_delete=True)


class RunDataSource(StrEnum):
    GOOGLE_HEALTH = "googleHealth"
    RUNTRACKER = "runTracker"


class Run(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    userId: int | None = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: User | None = Relationship(back_populates="runs")
    dataSource: RunDataSource = Field(sa_column=Column(SQLEnum(RunDataSource), nullable=False))
    startTime: datetime
    endTime: datetime
    calories: int | None
    distanceMillimeters: int
    averagePaceSecondsPerMeter: float
    steps: int | None
    elevationGainMillimeters: int | None
    activeDuration: int
    avgCadenceStepsPerMinute: int | None
    avgStrideLengthMillimeters: int | None
    avgVerticalOscillationMillimeters: int | None
    avgVerticalRatio: float | None
    avgGroundContactTimeDuration: float | None


class Error(BaseModel):
    title: str
    detail: str | None = None
    source: str | None = None
