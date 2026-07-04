import asyncio
import contextlib
from collections.abc import AsyncIterable
from enum import StrEnum
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from rungoal.crud import get_user
from rungoal.database import get_engine
from rungoal.google import GoogleHealthClient
from rungoal.models import User
from rungoal.settings import settings
from rungoal.sync import sync_runs
from rungoal.utils import ProgressProtocol


@contextlib.contextmanager
def get_db():
    with Session(get_engine()) as session:
        yield session


class SyncTasks(StrEnum):
    find_start = "find_start"
    runs = "runs"
    runtracker = "runtracker"
    weather = "weather"
    tcx = "tcx"


class TaskSyncState(BaseModel):
    task: str
    value: int
    total: int | None


class SyncState(BaseModel):
    is_complete: bool = False
    tasks: list[TaskSyncState] = Field(default=[])


class WebProgress(ProgressProtocol):
    def __init__(self):
        self.state = SyncState()
        self._listeners: list[asyncio.Queue] = []

    def start_task(self, task: str, total: int | None) -> None:
        self.state.tasks.append(TaskSyncState(task=task, value=0, total=total))
        self._broadcast()

    def advance(self, task: str) -> None:
        t = next(t for t in self.state.tasks if t.task == task)
        t.value += 1
        self._broadcast()

    def set_complete(self) -> None:
        self.state.is_complete = True
        self._broadcast()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        queue.put_nowait(self.state)
        self._listeners.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._listeners:
            self._listeners.remove(queue)

    def _broadcast(self):
        for queue in self._listeners:
            queue.put_nowait(self.state)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


_syncs_in_progress: dict[int, "SyncOperation"] = {}


class SyncOperation:
    def __init__(self, user_id: int, runtracker_email: str | None = None):
        self.user_id, self.runtracker_email = user_id, runtracker_email
        self.progress = WebProgress()
        asyncio.create_task(self._run_sync())

    def _run_sync_thread(self, user_id: int):
        with get_db() as db:
            user = get_user(db, user_id)
            with GoogleHealthClient(user, db) as client:
                sync_runs(
                    client,
                    self.progress,
                    runtracker_db_path=Path(settings.RUNTRACKER_DB)
                    if not user.is_onboarded
                    else None,
                )
                if not user.is_onboarded:
                    user.is_onboarded = True
                    db.commit()

    async def _run_sync(self):
        try:
            await asyncio.to_thread(self._run_sync_thread, self.user_id)
        except Exception as e:
            e.add_note(f"userid={self.user_id}, email={self.runtracker_email}")
            raise
        finally:
            # Notify everyone we're complete
            self.progress.set_complete()
            del _syncs_in_progress[self.user_id]


# Returns the status of the current sync operation. If no sync
# is in progress, returns a completed SyncProgress.
def sync_status(user_id: int) -> SyncState:
    if user_id not in _syncs_in_progress:
        return SyncState(is_complete=True)
    return _syncs_in_progress[user_id].progress.state


# Starts a sync, if one is not already in progress.
async def sync_start(user: User, include_runtracker: bool):
    assert user.id is not None
    if user.id not in _syncs_in_progress:
        _syncs_in_progress[user.id] = SyncOperation(
            user.id, user.email if include_runtracker else None
        )


# Returns the sync progress stream. If no sync is in progress, returns
# HTTP 409 Conflict.
async def sync_stream(user_id: int) -> AsyncIterable[SyncState]:
    if user_id not in _syncs_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No sync in progress",
        )
    sync = _syncs_in_progress[user_id]
    queue = sync.progress.subscribe()

    try:
        while True:
            progress = await queue.get()
            yield progress

            if progress.is_complete:
                break

    except asyncio.CancelledError:
        # Client closed connection
        pass
    finally:
        sync.progress.unsubscribe(queue)
