from collections.abc import Sequence
from math import sqrt
from typing import cast

from PIL import Image
from sqlmodel import col, select

from .database import get_db
from .heatmap import heatmap
from .models import Run, TrackPoint

# Based on max 100 trackpoints on a single spot at zoom level 15
_heatmap_scale_factor = {i: 100 * (2.0 ** (15 - i)) for i in range(21)}


def get_trackpoints() -> Sequence[tuple[float, float]]:
    with get_db() as db:
        return cast(
            Sequence[tuple[float, float]],
            db.exec(
                select(TrackPoint.lat_deg, TrackPoint.lon_deg)
                .join(Run, isouter=True)
                .where(col(TrackPoint.lat_deg).is_not(None))
                .where(col(TrackPoint.lon_deg).is_not(None))
                .where(Run.id == 739)
            ).all(),
        )


def make_blob():
    img = Image.new("L", (256, 256), 255)
    if buf := img.load():
        for x in range(256):
            for y in range(256):
                xd, yd = abs(128 - x), abs(128 - y)
                buf[x, y] = 256 - int(sqrt(xd * xd + yd * yd) * 2)
    img.save("assets/heatmap-point.png", "PNG")


img = heatmap(9043, 12963, 15, get_trackpoints())
img.save("tmp2.png", "PNG")
