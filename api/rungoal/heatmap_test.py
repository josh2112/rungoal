import time
from collections.abc import Sequence
from math import sqrt
from typing import cast

from mercantile import LngLatBbox
from PIL import Image, ImageMath
from sqlmodel import col, select

from .database import get_db
from .models import Run, TrackPoint

bbox = LngLatBbox(
    west=-80.650634765625,
    south=35.137879119634185,
    east=-80.6396484375,
    north=35.146862906756304,
)


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


def heatmap(img_size: tuple[int, int] = (256, 256), point_size: int = 32) -> Image.Image:
    t = time.time()
    pw, ph = point_size, point_size
    img = Image.new("I", img_size, 0)
    point = Image.open("assets/heatmap-point.png").resize((pw, ph)).convert("I")

    pts = get_trackpoints()

    bbox_w_factor, bbox_h_factor = (
        img.width / (bbox.east - bbox.west),
        img.height / (bbox.north - bbox.south),
    )

    for lat, lon in pts:
        if not (bbox.west <= lon <= bbox.east) or not (bbox.south <= lat <= bbox.north):
            continue

        px = (lon - bbox.west) * bbox_w_factor
        py = img.height - (lat - bbox.south) * bbox_h_factor

        x, y = int(x - pw / 2), int(y - ph / 2)
        crop = img.crop((x, y, x + pw, y + ph))
        added_crop = ImageMath.unsafe_eval("A+B", A=crop, B=point)
        img.paste(added_crop, (x, y))

    vmax = cast(int, img.getextrema()[1])
    scale = 255.0 / vmax

    img = img.point(lambda v: v * scale).convert(mode="L")
    print("Make heatmap:", time.time() - t)
    return img


def recolor(img: Image.Image):
    t = time.time()
    img = img.convert("P")
    lut = Image.open("assets/heatmap-lut.png").convert("RGBA")
    img.putpalette(lut.tobytes(), "RGBA")

    img = img.convert("RGBA")
    print("Recolor:", time.time() - t)

    img.save("tmp2.png")


recolor(heatmap())
