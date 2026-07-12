import asyncio
import contextlib
from collections.abc import AsyncIterable
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from rungoal.crud import get_user
from rungoal.database import get_engine
from rungoal.google import GoogleHealthClient
from rungoal.settings import settings
from rungoal.sync import sync_runs
from rungoal.utils import ProgressProtocol, TimeRange


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
    tasks: list[TaskSyncState] = Field(default=[])
    is_syncing: bool = True
    synced_from: datetime | None = None
    synced_to: datetime | None = None


class WebProgress(ProgressProtocol):
    def __init__(self):
        self.state = SyncState()
        self.loop = asyncio.get_running_loop()
        self._listeners: list[asyncio.Queue] = []

    def start_task(self, task: str, total: int | None) -> None:
        self.state.tasks.append(TaskSyncState(task=task, value=0, total=total))
        self._broadcast()

    def advance(self, task: str) -> None:
        t = next(t for t in self.state.tasks if t.task == task)
        t.value += 1
        self._broadcast()

    def complete_task(self, task: str) -> None:
        t = next(t for t in self.state.tasks if t.task == task)
        t.total = t.total if t.total else 1
        t.value = t.total
        self._broadcast()

    def set_complete(self, span: TimeRange) -> None:
        self.state.is_syncing = False
        self.state.synced_from = span.start
        self.state.synced_to = span.end
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
            self.loop.call_soon_threadsafe(queue.put_nowait, self.state.model_copy(deep=True))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


_syncs_in_progress: dict[int, "SyncOperation"] = {}


class SyncParams(BaseModel):
    user_id: int
    from_: datetime | None
    to: datetime | None
    include_runtracker: bool


class SyncOperation:
    def __init__(self, params: SyncParams):
        self.progress = WebProgress()
        asyncio.create_task(self._run_sync(params))

    def _run_sync_thread(self, params: SyncParams):
        with get_db() as db:
            user = get_user(db, params.user_id)
            with GoogleHealthClient(user, db) as client:
                span = sync_runs(
                    client,
                    self.progress,
                    from_=params.from_,
                    to=params.to,
                    tcx=False,
                    wx=False,
                    runtracker_db_path=Path(settings.RUNTRACKER_DB)
                    if params.include_runtracker
                    else None,
                )
                # The first sync means onboarding is completed
                if not user.is_onboarded:
                    user.is_onboarded = True
                    db.commit()
                self.progress.set_complete(span)

    async def _run_sync(self, params: SyncParams):
        try:
            await asyncio.to_thread(self._run_sync_thread, params)
        except Exception as e:
            e.add_note(f"userid={params.user_id}")
            raise
        finally:
            await asyncio.sleep(0.2)  # Give the sync-complete message a chance to be sent
            # Notify everyone we're complete
            del _syncs_in_progress[params.user_id]


# Returns the status of the current sync operation. If no sync
# is in progress, returns a completed SyncProgress.
def sync_status(user_id: int) -> SyncState:
    if user_id not in _syncs_in_progress:
        return SyncState(is_syncing=False)
    return _syncs_in_progress[user_id].progress.state


# Starts a sync, if one is not already in progress.
async def sync_start(
    user_id: int, from_: datetime | None, to: datetime | None, include_runtracker: bool
):
    if user_id not in _syncs_in_progress:
        _syncs_in_progress[user_id] = SyncOperation(
            SyncParams(user_id=user_id, from_=from_, to=to, include_runtracker=include_runtracker)
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

            if not progress.is_syncing:
                while True:
                    await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass
    finally:
        sync.progress.unsubscribe(queue)
