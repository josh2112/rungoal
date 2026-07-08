from datetime import datetime
from typing import Any, Sequence

from sqlmodel import Session, select

from rungoal.errors import RecordNotFoundError
from rungoal.models import Run, User, UserWithGoogleCreds


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


def get_runs(db: Session, user_id: int, from_: datetime, to: datetime) -> Sequence[Run]:
    return db.exec(
        select(Run)
        .where(Run.user_id == user_id)
        .where(Run.start_time >= from_)
        .where(Run.start_time <= to)
    ).all()
