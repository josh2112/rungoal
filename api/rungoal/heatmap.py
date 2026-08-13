import io

from PIL import Image, ImageDraw
from sqlmodel import Session

from .models import RequestUser


def build_heatmap_tile(db: Session, user: RequestUser, z: int, x: int, y: int):
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
