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


def get_trackpoints():
    with get_db() as db:
        trackpoints = db.exec(
            select(TrackPoint.lat_deg, TrackPoint.lon_deg)
            .join(Run, isouter=True)
            .where(col(TrackPoint.lat_deg).is_not(None))
            .where(col(TrackPoint.lon_deg).is_not(None))
            .where(Run.id == 739)
        ).all()


def make_blob():
    img = Image.new("LA", (256, 256), 255)
    if buf := img.load():
        for x in range(256):
            for y in range(256):
                xd, yd = abs(128 - x), abs(128 - y)
                buf[x, y] = (255, 256 - int(sqrt(xd * xd + yd * yd) * 2))
    img.save("assets/heatmap-point.png", "PNG")


def try_heatmap():
    pw, ph = 32, 32
    img = Image.new("I", (256, 256), 0)
    point = Image.open("assets/heatmap-point.png").resize((pw, ph)).convert("I")

    for x, y in ((112, 112), (112, 144), (144, 112), (144, 144)):
        crop = img.crop((x - pw / 2, y - ph / 2, x + pw / 2, y + ph / 2))
        merged_layers = Image.merge("I;16", (crop, point))
        added_crop = ImageMath.lambda_eval .eval("A + B", A=crop, B=point)
        img.paste(added_crop, (x, y))

    vmax = cast(int, img.getextrema()[1])
    print(vmax)

    # img.point( lambda v: )
    # img.show()


try_heatmap()
