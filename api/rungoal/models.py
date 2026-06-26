from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, model_validator
from sqlalchemy import Column, Unicode
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from sqlmodel import AutoString, Field, Relationship, SQLModel
from sqlmodel import Enum as SQLEnum

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
    runs: list["Run"] = Relationship(back_populates="user", cascade_delete=True)
    goals: list["Goal"] = Relationship(back_populates="user", cascade_delete=True)


class RunDataSource(StrEnum):
    GOOGLE_HEALTH = "googleHealth"
    RUNTRACKER = "runTracker"


class Run(SQLModel, table=True):
    __tablename__: str = "run"

    id: int | None = Field(default=None, primary_key=True)

    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: User | None = Relationship(back_populates="runs")

    data_source: RunDataSource = Field(sa_column=Column(SQLEnum(RunDataSource), nullable=False))
    data_source_id: str

    start_time: datetime
    end_time: datetime
    calories: int | None
    distance_millimeters: int
    average_pace_seconds_per_meter: float
    steps: int | None
    elevation_gain_millimeters: int | None
    active_duration: float
    avg_cadence_steps_per_minute: int | None
    avg_stride_length_millimeters: int | None
    avg_vertical_oscillation_millimeters: int | None
    avg_vertical_ratio: float | None
    avg_ground_contact_time_duration: float | None

    track_points: list["TrackPoint"] = Relationship(back_populates="run", cascade_delete=True)


class TrackPoint(SQLModel, table=True):
    __tablename__: str = "trackpoint"

    id: int | None = Field(default=None, primary_key=True)

    run_id: int | None = Field(default=None, foreign_key="run.id", ondelete="CASCADE")
    run: Run | None = Relationship(back_populates="track_points")

    elapsed_secs: int
    lat_deg: float
    lon_deg: float
    alt_meters: float
    distance_meters: float
    heart_rate_bmp: int


class GoalCreate(SQLModel):
    start_date: date
    end_date: date
    distance_meters: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_dates(self) -> "GoalCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end date must be after start date")
        return self


class Goal(GoalCreate, table=True):
    id: int = Field(default=None, primary_key=True)

    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: User | None = Relationship(back_populates="goals")


class Error(BaseModel):
    title: str
    detail: str | None = None
    source: str | None = None
