import random
import time
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
    img = Image.new("L", (256, 256), 255)
    if buf := img.load():
        for x in range(256):
            for y in range(256):
                xd, yd = abs(128 - x), abs(128 - y)
                buf[x, y] = 256 - int(sqrt(xd * xd + yd * yd) * 2)
    img.save("assets/heatmap-point.png", "PNG")


def try_heatmap(img_size: tuple[int, int] = (256, 256), point_size: int = 32):
    t = time.time()
    pw, ph = point_size, point_size
    img = Image.new("I", img_size, 0)
    point = Image.open("assets/heatmap-point.png").resize((pw, ph)).convert("I")

    pts = [
        (
            random.random() * (img_size[0] - pw) + pw / 2,
            random.random() * (img_size[1] - ph) + ph / 2,
        )
        for _ in range(200)
    ]

    for x, y in pts:
        x, y = int(x - pw / 2), int(y - ph / 2)
        crop = img.crop((x, y, x + pw, y + ph))
        added_crop = ImageMath.unsafe_eval("A+B", A=crop, B=point)
        img.paste(added_crop, (x, y))

    vmax = cast(int, img.getextrema()[1])
    scale = 255.0 / vmax

    img = img.point(lambda v: v * scale).convert(mode="L")
    print("Elapsed", time.time() - t)
    img.save("tmp.png", "PNG")


def recolor():
    img = Image.open("tmp.png")
    data = Image.open("assets/heatmap-lut.png").get_flattened_data()
    r_channel = [pixel[0] for pixel in data]
    g_channel = [pixel[1] for pixel in data]
    b_channel = [pixel[2] for pixel in data]
    a_channel = [pixel[3] for pixel in data]

    correct_flat_lut = r_channel + g_channel + b_channel + a_channel

    img = img.point(correct_flat_lut, mode="RGBA")
    img.save("tmp2.png")


# try_heatmap()
recolor()
