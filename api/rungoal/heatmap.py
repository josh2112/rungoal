import asyncio
import io
import time
from collections.abc import Sequence
from typing import cast

import mercantile
from PIL import Image, ImageMath
from sqlmodel import Session, col, select

from .models import RequestUser, Run, TrackPoint

_trackpoint_cache: dict[int, Sequence[tuple[float, float]]] = {}

_cache_locks: dict[int, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()


# Based on max 100 trackpoints on a single spot at zoom level 15
_heatmap_scale_factor = {i: 100 * (2.0 ** (15 - i)) for i in range(21)}


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

        _trackpoint_cache[user_id] = cast(
            Sequence[tuple[float, float]],
            await asyncio.to_thread(
                lambda: db.exec(
                    select(TrackPoint.lat_deg, TrackPoint.lon_deg)
                    .join(Run, isouter=True)
                    .where(col(TrackPoint.lat_deg).is_not(None))
                    .where(col(TrackPoint.lon_deg).is_not(None))
                    .where(Run.user_id == user_id)
                ).all()
            ),
        )

        del _cache_locks[user_id]
        return _trackpoint_cache[user_id]


def heatmap(
    tx: int,
    ty: int,
    tz: int,
    pts: Sequence[tuple[float, float]],
    img_size: tuple[int, int] = (256, 256),
    point_size: int = 16,
) -> Image.Image:
    t = time.time()
    pw, ph = point_size, point_size
    img = Image.new("I", img_size, 0)
    point = Image.open("assets/heatmap-point.png").resize((pw, ph)).convert("I")

    bbox = mercantile.bounds(tx, ty, tz)

    bbox_w_factor, bbox_h_factor = (
        img.width / (bbox.east - bbox.west),
        img.height / (bbox.north - bbox.south),
    )

    for lat, lon in pts:
        if not (bbox.west <= lon <= bbox.east) or not (bbox.south <= lat <= bbox.north):
            continue

        x, y = (
            int((lon - bbox.west) * bbox_w_factor - pw / 2),
            int(img.height - (lat - bbox.south) * bbox_h_factor - ph / 2),
        )

        crop = img.crop((x, y, x + pw, y + ph))
        added_crop = ImageMath.lambda_eval(lambda _: _["a"] + _["b"], a=crop, b=point)
        img.paste(added_crop, (x, y))

    img = img.point(lambda v: v / _heatmap_scale_factor[tz]).convert(mode="L")
    print("Make heatmap:", time.time() - t)
    return img


def recolor(img: Image.Image):
    t = time.time()
    img = img.convert("P")
    lut = Image.open("assets/heatmap-lut.png")
    img.putpalette(lut.tobytes(), "RGBA")

    print("Recolor:", time.time() - t)
    return img


async def build_heatmap_tile(db: Session, user: RequestUser, z: int, x: int, y: int):
    trackpoints = await _get_user_trackpoints_cached(user.id, db)

    img = recolor(heatmap(x, y, z, trackpoints))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
