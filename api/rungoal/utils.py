from collections.abc import Iterable
from datetime import datetime, timedelta


class TimeRange:
    def __init__(
        self, start: datetime, end: datetime | None = None, duration: timedelta | None = None
    ):
        if not end and not duration:
            raise Exception("Must include either [end] or [duration]")
        self.start = start
        self.end: datetime = start + duration if duration else end

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
