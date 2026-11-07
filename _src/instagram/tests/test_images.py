"""Photos come out upright, at most 1400px, under 400 KB, with no metadata; file names come from the caption."""
import datetime
import io

import pytest
from PIL import Image

from images import MAX_BYTES, ImageError, file_name, process_image, slug


def gradient(w, h):
    g = Image.linear_gradient("L").resize((w, h))
    return Image.merge("RGB", (g, g.rotate(90, expand=False).resize((w, h)), g.transpose(Image.FLIP_LEFT_RIGHT)))


def noise(w, h):
    return Image.effect_noise((w, h), 80).convert("RGB")


def encode(img, fmt="JPEG", **kw):
    buf = io.BytesIO()
    img.save(buf, fmt, **kw)
    return buf.getvalue()


def opened(data):
    return Image.open(io.BytesIO(data))


def test_resizes_long_side_to_1400():
    out = opened(process_image(encode(gradient(2800, 2100))))
    assert out.size == (1400, 1050) and out.format == "JPEG"


def test_never_upscales():
    assert opened(process_image(encode(gradient(1000, 800)))).size == (1000, 800)


def test_png_becomes_jpeg():
    png = encode(Image.new("RGBA", (1200, 900), (200, 30, 30, 128)), "PNG")
    out = opened(process_image(png))
    assert out.format == "JPEG" and out.mode == "RGB" and out.size == (1200, 900)


def test_exif_rotation_applied_and_stripped():
    exif = Image.Exif()
    exif[0x0112] = 6              # orientation: rotate 90 degrees clockwise to display
    exif[0x010F] = "PhoneMaker"   # make
    data = encode(gradient(1600, 1200), exif=exif.tobytes(), comment=b"shot at the studio")
    out = opened(process_image(data))
    assert out.size == (1050, 1400)
    assert dict(out.getexif()) == {}
    assert "icc_profile" not in out.info and "comment" not in out.info


def test_under_400kb_for_a_normal_photo():
    assert len(process_image(encode(gradient(4000, 3000), quality=95))) <= MAX_BYTES


def test_noise_image_steps_quality_down():
    big = noise(2000, 1500)
    at_85 = len(encode(big.resize((1400, 1050)), quality=85, optimize=True, progressive=True))
    out = process_image(encode(big, quality=95))
    assert opened(out).size == (1400, 1050)
    assert len(out) < at_85          # quality was lowered because 85 was over the cap


def test_rejects_small():
    with pytest.raises(ImageError, match="too small"):
        process_image(encode(gradient(500, 400)))


def test_rejects_garbage():
    with pytest.raises(ImageError, match="not an image"):
        process_image(b"not an image")


def test_slug():
    assert slug("Had a lot of fun doing this twisty snake from my flash, on the forearm") == "twisty-snake-flash"
    assert slug("Portrait of a dad and his baby, black and grey, inner forearm") == "portrait-dad-baby"
    assert slug("On the forearm") == "tattoo"


def test_file_name_and_clash():
    when = datetime.date(2026, 11, 7)
    caption = "Had a lot of fun doing this twisty snake from my flash, on the forearm"
    assert file_name(caption, when, lambda n: False) == "tattoo-preston-twisty-snake-flash-20261107.jpg"
    taken = {"tattoo-preston-twisty-snake-flash-20261107.jpg"}
    assert file_name(caption, when, lambda n: n in taken) == "tattoo-preston-twisty-snake-flash-20261107-2.jpg"
    taken.add("tattoo-preston-twisty-snake-flash-20261107-2.jpg")
    assert file_name(caption, when, lambda n: n in taken) == "tattoo-preston-twisty-snake-flash-20261107-3.jpg"
