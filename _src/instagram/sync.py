"""One hourly run: Caitlin's new Instagram photo posts that carry a usable line go onto the site,
edited captions follow, and deleted posts (or lines taken out) come off again.

    python -I _src/instagram/sync.py [--dry-run]
    python -I _src/instagram/sync.py --fixture posts.json --images DIR --repo DIR --since ISO [--now ISO]

Exit 0 when the run went through (whether or not anything changed), 2 when the Instagram
connection needs setting up again, 1 on any other failure (the next hour retries).
When GITHUB_OUTPUT is set, writes rebuild=, changed= and message= for the workflow.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mail                                             # noqa: E402
from api import Api, ApiError, parse_timestamp          # noqa: E402
from gallery import add_photo, remove_photo, set_caption  # noqa: E402
from gate import load_rules, pages_for, site_caption    # noqa: E402
from images import ImageError, file_name, process_image  # noqa: E402
from state import STATE_FILE, load_state, save_state    # noqa: E402
from tokenstore import TOKEN_FILE, TokenError, decrypt_token, encrypt_token  # noqa: E402

HOME = "00-home.html"
RECENT_HEADING = "recent-h"
SUBJECT_HEADING = "photos-h"
REFRESH_AFTER = datetime.timedelta(days=7)
EXISTENCE_CHECK_HOUR = 4          # once a day, on the 04:17 run
DIGEST_DAY, DIGEST_HOURS = 6, (18, 19)   # Sunday evening
DIGEST_GAP = datetime.timedelta(days=6)
DIGEST_WINDOW = datetime.timedelta(days=7)
RECONNECT = "The Instagram connection needs setting up again. Run connect.py."


class SyncError(Exception):
    pass


@dataclass
class Report:
    added: list = field(default_factory=list)      # (file, caption), newest first
    updated: list = field(default_factory=list)    # files whose caption changed
    removed: list = field(default_factory=list)    # files taken off the site
    skipped: list = field(default_factory=list)    # (post id, reason)
    notes: list = field(default_factory=list)
    rebuild: bool = False
    changed: bool = False
    commit_message: str = ""


def commit_message(rep):
    parts = ([f"add {caption}" for _, caption in rep.added]
             + [f"update {f}" for f in rep.updated]
             + [f"remove {f}" for f in rep.removed])
    if "token refreshed" in rep.notes:
        parts.append("token refreshed")
    if any(note.startswith("digest sent") for note in rep.notes):
        parts.append("weekly digest sent")
    if not parts:
        return ""
    return ("Instagram: " + "; ".join(parts))[:72].rstrip()


def iso(dt):
    return dt.isoformat()


def pick_photo(m):
    """The photo to use for a post, or the reason there is none."""
    kind = m.get("media_type")
    if kind == "IMAGE":
        return (m.get("media_url"), None) if m.get("media_url") else (None, "no photo")
    if kind == "CAROUSEL_ALBUM":
        for child in (m.get("children") or {}).get("data", []):
            if child.get("media_type") == "IMAGE" and child.get("media_url"):
                return child["media_url"], None
        return None, "no photo"
    if kind == "VIDEO":
        return None, "video"
    return None, "not a photo"


class Pages:
    """The page bodies, read on demand and written back once at the end."""

    def __init__(self, pages_dir):
        self.dir = pages_dir
        self.text = {}
        self.crlf = {}
        self.dirty = set()

    def names(self):
        return sorted(p.name for p in self.dir.glob("*.html"))

    def get(self, name):
        if name not in self.text:
            raw = (self.dir / name).read_text(encoding="utf-8", newline="")
            self.crlf[name] = "\r\n" in raw
            self.text[name] = raw.replace("\r\n", "\n")
        return self.text[name]

    def set(self, name, text):
        if text != self.get(name):
            self.text[name] = text
            self.dirty.add(name)

    def write(self):
        for name in self.dirty:
            text = self.text[name]
            if self.crlf[name]:
                text = text.replace("\n", "\r\n")
            (self.dir / name).write_text(text, encoding="utf-8", newline="")


def run(repo, now, api, rules, state, dry_run, mailer, existence_check=None,
        token=None, token_key=None, token_file=None):
    rep = Report()
    if not state.get("since"):
        raise SyncError("no switch-on date in state.json")
    if dry_run:
        state = json.loads(json.dumps(state))      # work on a copy; the caller's state stays as it was
    since = datetime.datetime.fromisoformat(state["since"])
    posts = state["posts"]
    pages = Pages(repo / "_src" / "pages")
    images = repo / "images"
    state_changed = False

    # The token: refreshed once a week, so it never gets near its 60-day end while the robot runs.
    if token and token_key and token_file and not dry_run:
        last = state.get("token_refreshed")
        if not last or now - datetime.datetime.fromisoformat(last) > REFRESH_AFTER:
            new_token, expires_in = api.refresh()
            token_file.parent.mkdir(parents=True, exist_ok=True)
            token_file.write_bytes(encrypt_token(new_token, token_key))
            state["token_refreshed"] = iso(now)
            state["token_expires"] = iso(now + datetime.timedelta(seconds=expires_in))
            state_changed = True
            rep.notes.append("token refreshed")

    def take_down(post_id, rec):
        for name in pages.names():
            pages.set(name, remove_photo(pages.get(name), rec["file"]))
        if not dry_run and (images / rec["file"]).exists():
            (images / rec["file"]).unlink()
        rec["status"] = "removed"
        rep.removed.append(rec["file"])
        rep.rebuild = True

    media = api.fetch_media()
    fetched_ids = {m["id"] for m in media}
    new_live = []          # (timestamp, post id, record), to be added oldest first
    candidates = []        # photo posts without a line, for the weekly digest

    for m in media:
        ts = parse_timestamp(m["timestamp"])
        if ts < since:
            continue
        rec = posts.get(m["id"])
        line = site_caption(m.get("caption"), rules)
        photo_url, reason = pick_photo(m)

        if rec and rec["status"] == "live":
            if line is None:
                take_down(m["id"], rec)
            elif line != rec["caption"]:
                for name in pages.names():
                    pages.set(name, set_caption(pages.get(name), rec["file"], line))
                rec["caption"] = line
                rep.updated.append(rec["file"])
                rep.rebuild = True
            continue

        if reason:
            rep.skipped.append((m["id"], reason))
            continue
        if line is None:
            rep.skipped.append((m["id"], "no line"))
            if now - ts <= DIGEST_WINDOW:
                candidates.append(((m.get("caption") or "(no caption)").strip()[:60], m.get("permalink")))
            continue
        new_live.append((ts, m, line, photo_url))

    taken = set()
    for ts, m, line, photo_url in sorted(new_live, key=lambda t: t[0]):
        try:
            data = api.download(photo_url)
            jpg = process_image(data)
        except ImageError as e:
            rep.skipped.append((m["id"], str(e)))
            continue
        except Exception as e:                     # a CDN hiccup: try again next hour
            rep.skipped.append((m["id"], f"download failed: {e}"))
            continue
        file = file_name(line, ts.date(), lambda n: n in taken or (images / n).exists())
        taken.add(file)
        subject_pages = pages_for(line, rules)
        pages.set(HOME, add_photo(pages.get(HOME), RECENT_HEADING, file, line, keep=rules["home_count"]))
        for name in subject_pages:
            pages.set(name, add_photo(pages.get(name), SUBJECT_HEADING, file, line, keep=None))
        if not dry_run:
            (images / file).write_bytes(jpg)
        posts[m["id"]] = {"status": "live", "file": file, "caption": line, "permalink": m.get("permalink"),
                          "timestamp": m["timestamp"], "pages": subject_pages}
        rep.added.insert(0, (file, line))
        rep.rebuild = True
    if not dry_run:
        for file, line in rep.added:
            rec = next(r for r in posts.values() if r.get("file") == file)
            mailer(*mail.went_live(line, rec["permalink"]))

    # Once a day, is every photo we put up still on Instagram?
    if existence_check is None:
        existence_check = now.hour == EXISTENCE_CHECK_HOUR
    if existence_check:
        for post_id, rec in list(posts.items()):
            if rec["status"] == "live" and post_id not in fetched_ids:
                try:
                    if not api.media_exists(post_id):
                        take_down(post_id, rec)
                except ApiError as e:
                    if e.is_auth:
                        raise
                    rep.notes.append(f"could not check {post_id}: {e}")

    # Sunday evening: the photo posts of the week that had no line, so she can add one.
    if (not dry_run and now.weekday() == DIGEST_DAY and now.hour in DIGEST_HOURS and candidates):
        last = state.get("last_digest")
        if not last or now - datetime.datetime.fromisoformat(last) > DIGEST_GAP:
            if mailer(*mail.digest(candidates)):
                state["last_digest"] = iso(now)
                state_changed = True
                rep.notes.append(f"digest sent: {len(candidates)} posts without a line")

    if not dry_run:
        pages.write()
    rep.changed = (not dry_run) and (rep.rebuild or state_changed)
    rep.rebuild = rep.rebuild and not dry_run
    rep.commit_message = commit_message(rep)
    return rep


class FixtureApi:
    """Canned posts and local photos, for dry runs without Instagram."""

    def __init__(self, fixture, images_dir):
        self.media = json.loads(pathlib.Path(fixture).read_text(encoding="utf-8"))
        self.images_dir = pathlib.Path(images_dir)

    def fetch_media(self, limit=25):
        return self.media

    def media_exists(self, media_id):
        return any(m["id"] == media_id for m in self.media)

    def refresh(self):
        return "FIXTURE", 5183944

    def download(self, url):
        return (self.images_dir / url.rsplit("/", 1)[-1]).read_bytes()


def print_report(rep, dry_run):
    verb = (lambda v: f"would {v}") if dry_run else (lambda v: v + ("d" if v.endswith("e") else "ed"))
    for file, caption in rep.added:
        print(f"{verb('add')} {file}: {caption}")
    for file in rep.updated:
        print(f"{verb('update')} {file}")
    for file in rep.removed:
        print(f"{verb('remove')} {file}")
    for post_id, reason in rep.skipped:
        print(f"skip {post_id}: {reason}")
    for note in rep.notes:
        print(note)
    print(f"rebuild={str(rep.rebuild).lower()} changed={str(rep.changed).lower()}"
          + (f" message={rep.commit_message}" if rep.commit_message else ""))


def write_outputs(rep):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"rebuild={str(rep.rebuild).lower()}\n")
            f.write(f"changed={str(rep.changed).lower()}\n")
            f.write(f"message={rep.commit_message}\n")


def fail(reason):
    print(reason)
    mail.send(*mail.needs_reconnect(reason))
    write_outputs(Report())
    return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report what would happen; change nothing")
    ap.add_argument("--fixture", help="a JSON list of posts instead of Instagram")
    ap.add_argument("--images", help="folder of photos the fixture's media_url names point at")
    ap.add_argument("--repo", help="site checkout to work in (default: this one)")
    ap.add_argument("--since", help="switch-on moment for fixture runs, ISO 8601")
    ap.add_argument("--now", help="pretend it is this moment, ISO 8601")
    args = ap.parse_args(argv)

    repo = pathlib.Path(args.repo).resolve() if args.repo else HERE.parent.parent
    now = (datetime.datetime.fromisoformat(args.now) if args.now
           else datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0))
    rules = load_rules(HERE / "rules.json")

    if args.fixture:
        state = load_state(None)
        state["since"] = args.since or "2000-01-01T00:00:00+00:00"
        state_path = None
        api = FixtureApi(args.fixture, args.images)
        token = key = token_file = None
    else:
        key = os.environ.get("IG_TOKEN_KEY")
        if not key or not TOKEN_FILE.exists():
            return fail(RECONNECT)
        try:
            token = decrypt_token(TOKEN_FILE.read_bytes(), key)
        except TokenError:
            return fail(RECONNECT)
        state = load_state(STATE_FILE)
        state_path = STATE_FILE
        if not state.get("since"):
            return fail(RECONNECT)
        api = Api(token)
        token_file = TOKEN_FILE

    try:
        rep = run(repo, now, api, rules, state, args.dry_run, mail.send,
                  token=token, token_key=key, token_file=token_file)
    except ApiError as e:
        if e.is_auth:
            return fail(f"Instagram rejected the key ({e}). " + RECONNECT)
        raise
    except SyncError as e:
        return fail(f"{e}. " + RECONNECT)

    if rep.changed and state_path:
        save_state(state_path, state)
    print_report(rep, args.dry_run)
    write_outputs(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
