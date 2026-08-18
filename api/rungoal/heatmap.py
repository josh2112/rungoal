import asyncio
import io
from collections.abc import Sequence
from typing import cast

import mercantile
from PIL import Image, ImageMath
from sqlmodel import Session, col, select

from .models import RequestUser, Run, TrackPoint

# Based on max 100 trackpoints on a single spot at zoom level 15
_heatmap_scale_factor = {i: 100 * (2.0 ** (15 - i)) for i in range(21)}

_lut = Image.open("assets/heatmap-lut.png").tobytes()


_splat_cache: dict[int, Image.Image] = {256: Image.open("assets/heatmap-point.png").convert("I")}
_splat_cache_locks: dict[int, asyncio.Lock] = {}
_splat_meta_lock = asyncio.Lock()


async def _get_splat_cached(size: int) -> Image.Image:
    if size in _splat_cache:
        return _splat_cache[size]

    async with _splat_meta_lock:
        if size not in _splat_cache_locks:
            _splat_cache_locks[size] = asyncio.Lock()
        size_lock = _splat_cache_locks[size]

    async with size_lock:
        if size in _splat_cache:
            return _splat_cache[size]

        _splat_cache[size] = await asyncio.to_thread(lambda: _splat_cache[256].resize((size, size)))

        del _splat_cache_locks[size]
        return _splat_cache[size]


_trackpoint_cache: dict[int, Sequence[tuple[float, float]]] = {}
_trackpoint_cache_locks: dict[int, asyncio.Lock] = {}
_trackpoint_meta_lock = asyncio.Lock()


async def _get_user_trackpoints_cached(user_id: int, db: Session) -> Sequence[tuple[float, float]]:
    if user_id in _trackpoint_cache:
        return _trackpoint_cache[user_id]

    async with _trackpoint_meta_lock:
        if user_id not in _trackpoint_cache_locks:
            _trackpoint_cache_locks[user_id] = asyncio.Lock()
        user_lock = _trackpoint_cache_locks[user_id]

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

        del _trackpoint_cache_locks[user_id]
        return _trackpoint_cache[user_id]


def heatmap(
    tz: int,
    tx: int,
    ty: int,
    pts: Sequence[tuple[float, float]],
    splat: Image.Image,
    img_size: int = 256,
) -> Image.Image:

    sw, sh = splat.size
    if (sw, sh) == (0, 0) or sw.bit_count() != 1 or sh.bit_count() != 1:
        raise ValueError("splat image must be square with power-of-2 width and height")

    img = Image.new("I", (img_size + (sw << 1), img_size + (sh << 1)), 0)

    bbox = mercantile.bounds(tx, ty, tz)

    # Pad the bounding box
    bbox = mercantile.LngLatBbox(
        west=bbox.west - sw / img_size * (bbox.east - bbox.west),
        south=bbox.south - sw / img_size * (bbox.north - bbox.south),
        east=bbox.east + sw / img_size * (bbox.east - bbox.west),
        north=bbox.north + sw / img_size * (bbox.north - bbox.south),
    )

    bbox_w_factor, bbox_h_factor = (
        img.width / (bbox.east - bbox.west),
        img.height / (bbox.north - bbox.south),
    )

    sr = sw >> 1

    for lat, lon in pts:
        if not (bbox.west <= lon <= bbox.east) or not (bbox.south <= lat <= bbox.north):
            continue

        x = int((lon - bbox.west) * bbox_w_factor) - sr
        y = img.height - int((lat - bbox.south) * bbox_h_factor) - sr

        if x + sw >= img.width or y + sw >= img.height:
            continue

        crop = img.crop((x, y, x + sw, y + sw))
        added_crop = ImageMath.lambda_eval(lambda _: _["a"] + _["b"], a=crop, b=splat)
        img.paste(added_crop, (x, y))

    scale = _heatmap_scale_factor[tz]
    img = img.crop((sw, sw, img_size + sw, img_size + sw)).point(lambda v: v / scale).convert("P")

    img.putpalette(_lut, "RGBA")

    return img


async def build_heatmap_tile(db: Session, user: RequestUser, z: int, x: int, y: int):
    trackpoints = await _get_user_trackpoints_cached(user.id, db)
    splat = await _get_splat_cached(16)

    img = heatmap(z, x, y, trackpoints, splat)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
