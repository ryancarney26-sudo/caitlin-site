"""One-off: export Caitlin's Instagram photo posts back to a date, for backfilling the site.

    python -I _src/instagram/export.py --since 2026-05-07 --out export

Writes export/<post id>.jpg (upright, at most 1400px, under 400 KB, no metadata, exactly like every
site photo) and export/manifest.json (one row per post: id, caption, permalink, timestamp, media
type, file, and why a post has no file). Changes nothing on the site. It runs on GitHub, through
the "Instagram export" workflow, because that is where the Instagram key lives (IG_TOKEN_KEY).
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from api import Api                                       # noqa: E402
from images import ImageError, process_image              # noqa: E402
from sync import pick_photo                               # noqa: E402
from tokenstore import TOKEN_FILE, TokenError, decrypt_token  # noqa: E402


def parse_since(text):
    try:
        day = datetime.date.fromisoformat(text)
    except ValueError:
        raise SystemExit(f"--since must be a date like 2026-05-07, not {text!r}")
    return datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc)


def export(api, since, out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in api.fetch_media_since(since):
        row = {"id": m["id"], "caption": m.get("caption"), "permalink": m.get("permalink"),
               "timestamp": m["timestamp"], "media_type": m.get("media_type"), "file": None, "skip": None}
        url, reason = pick_photo(m)
        if reason:
            row["skip"] = reason
        else:
            try:
                jpg = process_image(api.download(url))
                row["file"] = f"{m['id']}.jpg"
                (out_dir / row["file"]).write_bytes(jpg)
            except ImageError as e:
                row["skip"] = str(e)
            except Exception as e:                        # a CDN hiccup on one photo is not fatal
                row["skip"] = f"download failed: {e}"
        rows.append(row)
    (out_dir / "manifest.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
                                           encoding="utf-8", newline="\n")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", required=True, help="oldest post date to export, YYYY-MM-DD")
    ap.add_argument("--out", required=True, help="folder for the photos and manifest.json")
    args = ap.parse_args(argv)
    since = parse_since(args.since)
    key = os.environ.get("IG_TOKEN_KEY")
    if not key or not TOKEN_FILE.exists():
        raise SystemExit("The Instagram connection isn't set up here (no IG_TOKEN_KEY or token.enc).")
    try:
        token = decrypt_token(TOKEN_FILE.read_bytes(), key)
    except TokenError:
        raise SystemExit("The Instagram key could not unlock token.enc.")
    rows = export(Api(token), since, args.out)
    photos = sum(1 for r in rows if r["file"])
    print(f"{len(rows)} posts since {since.date()}: {photos} photos exported, {len(rows) - photos} without a photo")
    for r in rows:
        if r["skip"]:
            print(f"  {r['id']} {r['timestamp'][:10]}: {r['skip']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
