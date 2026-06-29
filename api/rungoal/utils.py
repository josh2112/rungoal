from collections.abc import Iterable
from datetime import datetime, timedelta


class TimeRange:
    def __init__(
        self, start: datetime, end: datetime | None = None, duration: timedelta | None = None
    ):
        self.start = start
        if duration:
            self.end = start + duration
        elif end:
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
