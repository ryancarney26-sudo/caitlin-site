"""A one-off export of her photo posts since a date, for backfilling the site. Changes nothing on the site."""
import datetime
import io
import json

import pytest
from PIL import Image

from export import export, parse_since

SINCE = datetime.datetime(2026, 5, 7, tzinfo=datetime.timezone.utc)


def jpeg(colour, size=(1200, 1000)):
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "JPEG", quality=90)
    return buf.getvalue()


class ExportApi:
    def __init__(self, media, photos):
        self.media, self.photos, self.asked_since = media, photos, None

    def fetch_media_since(self, since):
        self.asked_since = since
        return self.media

    def download(self, url):
        data = self.photos[url]
        if isinstance(data, Exception):
            raise data
        return data


MEDIA = [
    {"id": "p1", "caption": "Healed rose 🌹", "media_type": "IMAGE", "media_url": "u/p1",
     "permalink": "https://www.instagram.com/p/one/", "timestamp": "2026-10-01T10:00:00+0000"},
    {"id": "p2", "caption": "Process video", "media_type": "VIDEO", "media_url": "u/p2.mp4",
     "permalink": "https://www.instagram.com/p/two/", "timestamp": "2026-09-01T10:00:00+0000"},
    {"id": "p3", "caption": None, "media_type": "CAROUSEL_ALBUM", "permalink": "https://www.instagram.com/p/three/",
     "timestamp": "2026-08-01T10:00:00+0000",
     "children": {"data": [{"id": "c1", "media_type": "VIDEO", "media_url": "u/c1.mp4"},
                           {"id": "c2", "media_type": "IMAGE", "media_url": "u/c2"}]}},
    {"id": "p4", "caption": "Tiny", "media_type": "IMAGE", "media_url": "u/p4",
     "permalink": "https://www.instagram.com/p/four/", "timestamp": "2026-07-01T10:00:00+0000"},
]


def test_export_writes_photos_and_a_manifest(tmp_path):
    api = ExportApi(MEDIA, {"u/p1": jpeg((200, 40, 40)), "u/c2": jpeg((40, 40, 200)),
                            "u/p4": jpeg((10, 10, 10), size=(300, 200))})
    rows = export(api, SINCE, tmp_path)
    assert api.asked_since == SINCE
    by_id = {r["id"]: r for r in rows}
    assert by_id["p1"]["file"] == "p1.jpg" and by_id["p1"]["skip"] is None
    assert by_id["p2"]["file"] is None and by_id["p2"]["skip"] == "video"
    assert by_id["p3"]["file"] == "p3.jpg"                      # the carousel's first photo
    assert by_id["p4"]["file"] is None and by_id["p4"]["skip"] == "too small"
    with Image.open(tmp_path / "p1.jpg") as im:
        assert im.format == "JPEG" and dict(im.getexif()) == {}
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == rows
    assert by_id["p1"]["caption"] == "Healed rose 🌹" and by_id["p1"]["permalink"].endswith("/one/")


def test_a_failed_download_is_recorded_not_fatal(tmp_path):
    api = ExportApi(MEDIA[:1], {"u/p1": OSError("timed out")})
    rows = export(api, SINCE, tmp_path)
    assert rows[0]["file"] is None and rows[0]["skip"].startswith("download failed")


def test_parse_since():
    assert parse_since("2026-05-07") == SINCE
    with pytest.raises(SystemExit):
        parse_since("7 May")
