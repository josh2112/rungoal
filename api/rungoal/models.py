from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, model_validator
from sqids import Sqids
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from sqlmodel import AutoString, Field, Relationship, SQLModel
from sqlmodel import Enum as SQLEnum

from .geometry import MultiPolygon
from .settings import settings

sqids = Sqids()


def hash_id(id):
    return sqids.encode([id])


class UTCDateTime(sa.types.TypeDecorator):
    """
    A custom SQLAlchemy type that ensures datetime objects
    are timezone-aware (UTC) upon retrieval.
    """

    impl = sa.DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class DistanceUnit(StrEnum):
    meters = "meters"
    miles = "miles"


class TemperatureUnit(StrEnum):
    celsius = "celsius"
    fahrenheit = "fahrenheit"


# ========= Auth ========


class GoogleApiAuthCode(BaseModel):
    google_access_code: str


class AccessToken(BaseModel):
    access_token: str


# ========= DB ========

# TODO:

distance_unit: DistanceUnit | None = Field(sa_column=sa.Column(SQLEnum(DistanceUnit)))
temperature_unit: TemperatureUnit | None = Field(sa_column=sa.Column(SQLEnum(TemperatureUnit)))


class UserBase(SQLModel):
    name: str
    email: EmailStr = Field(index=True, unique=True, sa_type=AutoString)
    avatar_uri: str


class UserWithGoogleCreds(UserBase):
    google_api_access_token: str
    google_api_refresh_token: str = Field(
        sa_column=sa.Column(
            EncryptedType(sa.Unicode, settings.GOOGLE_REFRESH_TOKEN_KEY, AesEngine, "pkcs5")
        )
    )


class UserResponse(UserWithGoogleCreds):
    is_onboarded: bool = Field(
        default=False, sa_column=sa.Column(sa.Boolean(), server_default=sa.false())
    )


# ===== User =====


class User(UserResponse, table=True):
    id: int | None = Field(default=None, primary_key=True)
    runs: list["Run"] = Relationship(back_populates="user", cascade_delete=True)
    goals: list["Goal"] = Relationship(back_populates="user", cascade_delete=True)


class RequestUser(UserResponse):
    id: int
    timezone: str


# ===== Weather =====


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


# ========= Geo stuff =========


class RunLocationResponse(SQLModel):
    osm_id: str = Field(primary_key=True)
    name: str


class RunLocationBase(RunLocationResponse):
    boundary_text: str


class RunLocation(RunLocationBase, table=True):
    """A place (park, greenway, etc.) where we might have run. These map directly to OpenStreetMap features."""

    runs: list["Run"] = Relationship(back_populates="location")


class RunLocationWithBoundary(RunLocationBase):
    class Config:
        arbitrary_types_allowed = True

    boundary: MultiPolygon


class CachedArea(SQLModel, table=True):
    """Bounding boxes of previous OpenStreetMap feature searches."""

    id: int | None = Field(default=None, primary_key=True)
    bbox_text: str


class RunDataSource(StrEnum):
    GOOGLE_HEALTH = "googleHealth"
    RUNTRACKER = "runTracker"


class RecordingPlatform(StrEnum):
    FITBIT = "FITBIT"
    HEALTH_CONNECT = "HEALTH_CONNECT"
    RUNTRACKER = "RUNTRACKER"


class RecordingMethod(StrEnum):
    MANUAL = "MANUAL"
    ACTIVELY_MEASURED = "ACTIVELY_MEASURED"


class DeviceType(StrEnum):
    PHONE = "PHONE"
    WATCH = "WATCH"


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
    id: Annotated[str, BeforeValidator(lambda id: sqids.encode([id]))]
    weather: WeatherResponse | None = None
    split_stats: list["RunSplitStatsResponse"]
    device_type: DeviceType | None
    location: RunLocationResponse | None


class Run(RunBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    end_time: datetime = Field(sa_column=sa.Column(UTCDateTime(timezone=True)))

    # Used to sync runs... if we see an existing data_source_id with a later
    # update time, replace it
    update_time: datetime = Field(sa_column=sa.Column(UTCDateTime(timezone=True)))

    user_id: int | None = Field(index=True, default=None, foreign_key="user.id", ondelete="CASCADE")
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

    platform: RecordingPlatform | None = Field(sa_column=sa.Column(SQLEnum(RecordingPlatform)))
    recording_method: RecordingMethod | None = Field(sa_column=sa.Column(SQLEnum(RecordingMethod)))
    device_type: DeviceType | None = Field(sa_column=sa.Column(SQLEnum(DeviceType)))
    device_name: str | None

    track_points: list["TrackPoint"] = Relationship(
        back_populates="run",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "TrackPoint.elapsed_secs"},
    )
    split_stats: list["RunSplitStats"] = Relationship(
        back_populates="run",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "RunSplitStats.start_secs"},
    )
    weather: Weather | None = Relationship(back_populates="run", cascade_delete=True)

    location_id: str | None = Field(default=None, foreign_key="runlocation.osm_id")
    location: RunLocation | None = Relationship(back_populates="runs")

    __table_args__ = (sa.UniqueConstraint(*run_unique_constriant_columns, name="run_unique"),)


class NotableType(StrEnum):
    HOTTEST = "HOTTEST"
    COLDEST = "COLDEST"
    WETTEST = "WETTEST"
    EARLIEST = "EARLIEST"
    LATEST = "LATEST"
    LONGEST = "LONGEST"
    FASTEST = "FASTEST"
    MOST_EFFICIENT = "MOST_EFFICIENT"


class NotableRunsResponse(BaseModel):
    runs: dict[NotableType, RunResponse | None]


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
    lat_deg: float | None
    lon_deg: float | None
    alt_meters: float | None
    distance_meters: float | None
    heart_rate_bpm: int | None


class RunSplitStatsResponse(SQLModel):
    start_secs: int
    end_secs: int
    dist_meters: float
    gad_meters: float
    hr_avg: float
    efficiency: float  # meters per heartbeat


class RunSplitStats(RunSplitStatsResponse, table=True):
    id: int | None = Field(default=None, primary_key=True)

    run_id: int | None = Field(default=None, foreign_key="run.id", ondelete="CASCADE")
    run: Run | None = Relationship(back_populates="split_stats")

    __table_args__ = (sa.Index("idx_rss_run_efficiency", "run_id", "efficiency"),)


class Range(BaseModel):
    min: float
    max: float


class StatsRanges(BaseModel):
    efficiency: Range | None


class GoalCreate(SQLModel):
    start_date: date
    end_date: date
    name: str
    distance_meters: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_dates(self) -> "GoalCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end date must be after start date")
        return self


class GoalResponse(GoalCreate):
    class Config:
        from_attributes = True

    id: Annotated[str, BeforeValidator(lambda id: sqids.encode([id]))]
    current_distance_meters: float


class GoalUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    distance_meters: float | None
    name: str | None = None


class Goal(GoalCreate, table=True):
    id: int = Field(default=None, primary_key=True)

    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: User | None = Relationship(back_populates="goals")


class Error(BaseModel):
    title: str
    detail: str | None = None
    source: str | None = None


class SyncRequest(BaseModel):
    class Config:
        populate_by_name = True

    from_: datetime | None = Field(alias="from", default=None)
    to: datetime | None = None
    include_runtracker: bool


class SyncParams(SyncRequest):
    user_id: int
    timezone: ZoneInfo
