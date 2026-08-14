import asyncio
import io
from collections.abc import Sequence
from typing import cast

import mercantile
from PIL import Image, ImageDraw
from sqlmodel import Session, select

from .models import RequestUser, Run, TrackPoint

HOME = 35.186226, -80.612127

RECT = (35.2, -80.7, 35.1, -80.6)

_trackpoint_cache: dict[int, Sequence[tuple[float, float]]] = {}

_cache_locks: dict[int, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()


async def _get_user_trackpoints_cached(user_id: int, db: Session) -> Sequence[tuple[float, float]]:
    if user_id in _trackpoint_cache:
        return _trackpoint_cache[user_id]

    async with _meta_lock:
        if user_id not in _cache_locks:
            _cache_locks[user_id] = asyncio.Lock()
        user_lock = _cache_locks[user_id]

    async with user_lock:
        if user_id in _trackpoint_cache:
            return _trackpoint_cache[user_id]

        print("Caching trackpoints for user", user_id)
        _trackpoint_cache[user_id] = cast(
            Sequence[tuple[float, float]],
            await asyncio.to_thread(
                lambda: db.exec(
                    select(TrackPoint.lat_deg, TrackPoint.lon_deg)
                    .join(Run, isouter=True)
                    .where(TrackPoint.lat_deg != None)
                    .where(TrackPoint.lon_deg != None)
                    .where(Run.user_id == user_id)
                ).all()
            ),
        )

        del _cache_locks[user_id]
        return _trackpoint_cache[user_id]


async def build_heatmap_tile(db: Session, user: RequestUser, z: int, x: int, y: int):
    trackpoints = await _get_user_trackpoints_cached(user.id, db)

    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    bbox = mercantile.bounds(x, y, z)

    bbox_w_factor, bbox_h_factor = (
        img.width / (bbox.east - bbox.west),
        img.height / (bbox.north - bbox.south),
    )

    for lat, lon in trackpoints:
        px = (lon - bbox.west) * bbox_w_factor
        py = img.height - (lat - bbox.south) * bbox_h_factor

        if 0 <= px < 256 and 0 <= py < 256:
            draw.circle((int(px), int(py)), 6, (255, 0, 0, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
