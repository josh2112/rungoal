from datetime import UTC, date, datetime
from enum import StrEnum

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, EmailStr, model_validator
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from sqlmodel import AutoString, Field, Relationship, SQLModel
from sqlmodel import Enum as SQLEnum

from rungoal.settings import settings


class UTCDateTime(sa.types.TypeDecorator):
    """
    A custom SQLAlchemy type that ensures datetime objects
    are timezone-aware (UTC) upon retrieval.
    """

    impl = sa.DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):  # noqa: ARG002
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


# ========= Auth ========


class GoogleApiAuthCode(BaseModel):
    google_access_code: str


class AccessToken(BaseModel):
    access_token: str


# ========= DB ========


class UserResponse(SQLModel):
    name: str
    email: EmailStr = Field(index=True, unique=True, sa_type=AutoString)
    avatar_uri: str
    is_onboarded: bool = Field(
        default=False, sa_column=sa.Column(sa.Boolean(), server_default=sa.false())
    )


class UserWithGoogleCreds(UserResponse):
    google_api_access_token: str
    google_api_refresh_token: str = Field(
        sa_column=sa.Column(
            EncryptedType(sa.Unicode, settings.GOOGLE_REFRESH_TOKEN_KEY, AesEngine, "pkcs5")
        )
    )


class User(UserWithGoogleCreds, table=True):
    id: int | None = Field(default=None, primary_key=True)
    runs: list["Run"] = Relationship(back_populates="user", cascade_delete=True)
    goals: list["Goal"] = Relationship(back_populates="user", cascade_delete=True)


class WeatherBase(SQLModel):
    temp_c: float | None
    apparent_temp_c: float | None
    humidity_pct: float | None
    rain_mm: float | None
    cloud_cover_pct: float | None


class WeatherResponse(WeatherBase):
    pass


class Weather(WeatherBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    run_id: int | None = Field(default=None, foreign_key="run.id", ondelete="CASCADE")
    run: "Run" = Relationship(back_populates="weather")


class RunDataSource(StrEnum):
    GOOGLE_HEALTH = "googleHealth"
    RUNTRACKER = "runTracker"


# This unique constraint will help us match incoming duplicate (maybe updated) runs without ID.
run_unique_constriant_columns = ("user_id", "data_source", "data_source_id")


class RunBase(SQLModel):
    start_time: datetime = Field(sa_column=sa.Column(UTCDateTime(timezone=True)))
    utc_offset_seconds: int
    calories: int | None
    distance_millimeters: int
    average_pace_seconds_per_meter: float
    active_duration: float


class RunResponse(RunBase):
    id: int
    weather: WeatherResponse | None = None


class Run(RunBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    end_time: datetime = Field(sa_column=sa.Column(UTCDateTime(timezone=True)))

    # Used to sync runs... if we see an existing data_source_id with a later
    # update time, replace it
    update_time: datetime = Field(sa_column=sa.Column(UTCDateTime(timezone=True)))

    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: User | None = Relationship(back_populates="runs")

    data_source: RunDataSource = Field(sa_column=sa.Column(SQLEnum(RunDataSource), nullable=False))
    data_source_id: str

    steps: int | None
    elevation_gain_millimeters: int | None

    avg_cadence_steps_per_minute: int | None
    avg_stride_length_millimeters: int | None
    avg_vertical_oscillation_millimeters: int | None
    avg_vertical_ratio: float | None
    avg_ground_contact_time_duration: float | None

    track_points: list["TrackPoint"] = Relationship(back_populates="run", cascade_delete=True)
    weather: Weather | None = Relationship(back_populates="run", cascade_delete=True)

    __table_args__ = (sa.UniqueConstraint(*run_unique_constriant_columns, name="run_unique"),)


class RunFetchContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_source_id: str
    start_time: datetime
    end_time: datetime


class TrackPoint(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    run_id: int | None = Field(default=None, foreign_key="run.id", ondelete="CASCADE")
    run: Run | None = Relationship(back_populates="track_points")

    elapsed_secs: float
    lat_deg: float
    lon_deg: float
    alt_meters: float
    distance_meters: float
    heart_rate_bpm: int | None


class GoalCreate(SQLModel):
    start_date: date
    end_date: date
    distance_meters: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_dates(self) -> "GoalCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end date must be after start date")
        return self


class GoalResponse(GoalCreate):
    class Config:
        from_attributes = True

    id: int
    current_distance_meters: float


class Goal(GoalCreate, table=True):
    id: int = Field(default=None, primary_key=True)

    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: User | None = Relationship(back_populates="goals")


class Error(BaseModel):
    title: str
    detail: str | None = None
    source: str | None = None
