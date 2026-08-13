import io

import mercantile
from PIL import Image, ImageDraw
from sqlmodel import Session

from .models import RequestUser

HOME = 35.186226, -80.612127


def build_heatmap_tile(db: Session, user: RequestUser, z: int, x: int, y: int):
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bbox = mercantile.bounds(x, y, z)

    print(f"BBOX: {bbox.west}->{bbox.east}, {bbox.south}^{bbox.north}")

    if bbox.west <= HOME[1] <= bbox.east and bbox.south <= HOME[0] <= bbox.north:
        print("WE GOT IT")

    px = (HOME[1] - bbox.west) / (bbox.east - bbox.west) * img.width
    py = (HOME[0] - bbox.south) / (bbox.north - bbox.south) * img.height

    if 0 <= px < 256 and 0 <= py < 256:
        print("POINT AT", px, py)
        draw.point((px, py), (255, 0, 0, 255))
    else:
        print("FAILED: point at ", px, py)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
