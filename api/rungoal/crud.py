from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, text
from sqlalchemy import select as sa_select
from sqlmodel import Session, col, select

from rungoal.errors import RecordNotFoundError
from rungoal.models import Goal, GoalResponse, Run, User, UserWithGoogleCreds


def _add_record(db: Session, record: Any) -> Any:
    """Adds a record and commits it right away, refreshing it to get any newly-generated
    primary key"""
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise RecordNotFoundError({str(User.id): user_id})
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.exec(select(User).where(User.email == email)).one_or_none()


def create_user(db: Session, user: UserWithGoogleCreds) -> User:
    # Make a User out of this so we can get the ID
    return _add_record(db, User(**user.model_dump()))


def get_goals(db: Session, user_id: int) -> list[GoalResponse]:

    # SQLite3's date fuctions take an offset as "+/- X.Y hours"
    assert (tz_offset := datetime.now().astimezone().utcoffset())
    tz_offset = f"{tz_offset.total_seconds() / 3600} hours"

    # Offset each run's start_time (stored in UTC) by the time zone offset (which may
    # wrap the date), then we can get away with just comparing dates.
    expr_run_date = func.date(Run.start_time, tz_offset)

    # Sum millimeters (returning 0 if no matching rows) then convert to meters.
    expr_total_distance = (func.coalesce(func.sum(Run.distance_millimeters), 0) / 1000.0).label(
        "current_distance_meters"
    )

    # Look for runs whose start date (in local time zone) falls between the goal dates,
    # and sum the distances.
    stmt = (
        # This returns (Goal(...), current_distance_meters)
        select(Goal, expr_total_distance)
        .where(Goal.user_id == user_id)
        .join(
            Run,
            onclause=(expr_run_date >= Goal.start_date) & (expr_run_date <= Goal.end_date),
            isouter=True,
        )
        .group_by(text("Goal.id"))
        .order_by(col(Goal.start_date).desc())
    )

    return [
        GoalResponse(**g[0].model_dump(), current_distance_meters=cast(float, g[1]))
        for g in db.exec(stmt).all()
    ]


def get_runs(db: Session, user_id: int, from_: datetime, to: datetime) -> Sequence[Run]:
    return db.exec(
        select(Run)
        .where(Run.user_id == user_id)
        .where(Run.start_time >= from_)
        .where(Run.start_time <= to)
        .order_by(col(Run.start_time).desc())
    ).all()
