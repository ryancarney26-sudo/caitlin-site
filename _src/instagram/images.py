"""Photos on their way in: upright, at most 1400px on the long side, a progressive JPEG under
about 400 KB, and no metadata of any kind. Plus the file name a photo gets, from its caption.
"""
import io
import re

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1400
MIN_SIDE = 600
MAX_BYTES = 400_000
QUALITIES = (85, 80, 75, 70)

# Words that say nothing about the subject, dropped when a caption becomes a file name.
STOPWORDS = set("""
a an the of on in my from with and for piece pieces tattoo tattoos black grey gray colour color
this that his her their one some is it at to as by had has have lot lots fun doing did done do
love loved really so today yesterday finally got get little bit inner outer upper lower left
right side back front arm forearm leg thigh calf hand wrist neck chest shoulder foot ankle ribs
hip sternum knee shin elbow finger fingers ear head sleeve half full
""".split())


class ImageError(Exception):
    pass


def process_image(data):
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ImageError("not an image") from e
    img = ImageOps.exif_transpose(img)
    if max(img.size) < MIN_SIDE:
        raise ImageError("too small")
    img = img.convert("RGB")
    img.info.clear()
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    out = b""
    for quality in QUALITIES:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True,
                 exif=b"", icc_profile=None, comment=b"")
        out = buf.getvalue()
        if len(out) <= MAX_BYTES:
            break
    return out


def slug(caption):
    words = re.sub(r"[^a-z0-9 ]+", " ", caption.lower()).split()
    words = [w for w in words if w not in STOPWORDS]
    return "-".join(words[:3]) or "tattoo"


def file_name(caption, when, exists):
    base = f"tattoo-preston-{slug(caption)}-{when:%Y%m%d}"
    name = base + ".jpg"
    n = 2
    while exists(name):
        name = f"{base}-{n}.jpg"
        n += 1
    return name
