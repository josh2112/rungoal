import asyncio
import contextlib
from collections.abc import AsyncIterable
from enum import StrEnum

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from rungoal.database import get_engine
from rungoal.models import User


@contextlib.contextmanager
def get_db():
    with Session(get_engine()) as session:
        yield session


class SyncTasks(StrEnum):
    runs = "runs"
    runtracker = "runtracker"
    weather = "weather"
    tcx = "tcx"


class SyncProgress(BaseModel):
    is_complete: bool = False
    tasks: list[tuple[SyncTasks, float]] = Field(default=[])


_syncs_in_progress: dict[int, "SyncOperation"] = {}


class SyncOperation:
    def __init__(self, user_id: int, runtracker_email: str | None = None):
        self.user_id, self.runtracker_email = user_id, runtracker_email
        self.progress = SyncProgress()
        self._listeners: list[asyncio.Queue] = []

        self.task = asyncio.create_task(self._run_sync())

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        queue.put_nowait(self.progress)
        self._listeners.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._listeners:
            self._listeners.remove(queue)

    def _broadcast(self):
        for queue in self._listeners:
            queue.put_nowait(self.progress)

    async def _run_sync(self):
        try:
            # with get_db() as db:
            #     await asyncio.to_thread(sync_runs_function, db, self.user_id)

            self.progress.tasks.append((SyncTasks.runs, 0))
            for step in range(1, 11):
                await asyncio.sleep(1)
                self.progress.tasks[-1][1] = step / 10.0
                self._broadcast()

        except Exception as e:
            e.add_note(f"userid={self.user_id}, email={self.runtracker_email}")
            raise
        finally:
            # Notify everyone we're complete
            self.progress = SyncProgress(is_complete=True)
            self._broadcast()

            del _syncs_in_progress[self.user_id]


# Returns the status of the current sync operation. If no sync
# is in progress, resturns a completed SyncProgress.
def sync_status(user_id: int) -> SyncProgress:
    if user_id not in _syncs_in_progress:
        return SyncProgress(is_complete=True)
    return _syncs_in_progress[user_id].progress


# Starts a sync, if one is not already in progress.
async def sync_start(user: User, include_runtracker: bool):
    assert user.id is not None
    if user.id not in _syncs_in_progress:
        _syncs_in_progress[user.id] = SyncOperation(
            user.id, user.email if include_runtracker else None
        )


# Returns the sync progress stream. If no sync is in progress, resturns
# HTTP 409 Conflict.
async def sync_stream(user_id: int) -> AsyncIterable[SyncProgress]:
    if user_id not in _syncs_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No sync in progress",
        )
    sync = _syncs_in_progress[user_id]
    queue = sync.subscribe()

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
        sync.unsubscribe(queue)
