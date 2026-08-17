import asyncio
import io
from collections.abc import Sequence
from typing import cast

import mercantile
from PIL import Image, ImageMath
from sqlmodel import Session, col, select

from .models import RequestUser, Run, TrackPoint

_trackpoint_cache: dict[int, Sequence[tuple[float, float]]] = {}

_cache_locks: dict[int, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()

_point_img_cache: dict[int, Image.Image] = {
    256: Image.open("assets/heatmap-point.png").convert("I")
}

# Based on max 100 trackpoints on a single spot at zoom level 15
_heatmap_scale_factor = {i: 100 * (2.0 ** (15 - i)) for i in range(21)}

_lut = Image.open("assets/heatmap-lut.png").tobytes()


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
    img_size: int = 256,
    point_size: int = 16,
) -> Image.Image:

    img = Image.new("I", (img_size + point_size * 2, img_size + point_size * 2), 0)

    if point_size not in _point_img_cache:
        _point_img_cache[point_size] = _point_img_cache[256].resize((point_size, point_size))
    img_point = _point_img_cache[point_size]

    bbox = mercantile.bounds(tx, ty, tz)

    # Pad the bounding box
    bbox_w = bbox.east - bbox.west
    bbox_h = bbox.north - bbox.south
    pad_factor = point_size / img_size
    bbox = mercantile.LngLatBbox(
        west=bbox.west - pad_factor * bbox_w,
        south=bbox.south - pad_factor * bbox_h,
        east=bbox.east + pad_factor * bbox_w,
        north=bbox.north + pad_factor * bbox_h,
    )

    bbox_w_factor, bbox_h_factor = (
        img.width / (bbox.east - bbox.west),
        img.height / (bbox.north - bbox.south),
    )

    point_radius = point_size / 2

    for lat, lon in pts:
        if not (bbox.west <= lon <= bbox.east) or not (bbox.south <= lat <= bbox.north):
            continue

        x, y = (
            int((lon - bbox.west) * bbox_w_factor - point_radius),
            int(img.height - (lat - bbox.south) * bbox_h_factor - point_radius),
        )

        crop = img.crop((x, y, x + point_size, y + point_size))
        added_crop = ImageMath.lambda_eval(lambda _: _["a"] + _["b"], a=crop, b=img_point)
        img.paste(added_crop, (x, y))

    img = (
        img.crop((point_size, point_size, img_size + point_size, img_size + point_size))
        .point(lambda v: v / _heatmap_scale_factor[tz])
        .convert("P")
    )
    img.putpalette(_lut, "RGBA")

    return img


async def build_heatmap_tile(db: Session, user: RequestUser, z: int, x: int, y: int):
    trackpoints = await _get_user_trackpoints_cached(user.id, db)

    img = heatmap(x, y, z, trackpoints)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
