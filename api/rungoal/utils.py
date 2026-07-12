from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Protocol


class TimeRange:
    def __init__(
        self, start: datetime, end: datetime | None = None, duration: timedelta | None = None
    ):
        self.start = start
        if duration:
            self.end = start + duration
        elif end:
            if end < start:
                raise Exception("End time must be after start time")
            self.end = end
        else:
            raise Exception("Must include either [end] or [duration]")

    def overlaps(self, other: "TimeRange") -> bool:
        return self.end > other.start if self.start < other.start else self.start < other.end

    def chunk(self, duration: timedelta) -> Iterable["TimeRange"]:
        # Breaks up the TimeRange into multiple TimeRanges of a given size.
        cur = self.start
        nxt = self.start + duration
        while nxt < self.end:
            yield TimeRange(cur, end=nxt)
            cur = nxt
            nxt += duration
        yield TimeRange(cur, end=self.end)

    def __str__(self) -> str:
        return f"{self.start} -> {self.end}"


def block_overlap(values: list, start: float, end: float):
    if all(v is None for v in values):
        return None

    duration = max(end - start, 0.1)
    end = start + duration
    wt_sum = 0

    for i, value in enumerate(values):
        block = i - 0.5, i + 0.5
        overlap = min(end, block[1]) - max(start, block[0])

        if overlap > 0:
            wt_sum += value * overlap / duration

    return wt_sum


class ProgressProtocol(Protocol):
    def start_task(self, task: str, total: int | None) -> None: ...
    def advance(self, task: str) -> None: ...
    def complete_task(self, task: str) -> None: ...
