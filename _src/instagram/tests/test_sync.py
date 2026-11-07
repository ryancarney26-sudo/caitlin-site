"""One hourly run, end to end, against canned posts and generated photos."""
import copy
import datetime
import io
import json
import pathlib
import subprocess
import sys

import pytest
from PIL import Image

from gallery import gallery_lines
from gate import load_rules
from images import process_image
from state import load_state, save_state
from sync import Report, commit_message, run
from tokenstore import decrypt_token, encrypt_token, new_key

HERE = pathlib.Path(__file__).resolve().parent
RULES = load_rules(HERE.parent / "rules.json")
MEDIA = json.loads((HERE / "fixtures" / "media.json").read_text(encoding="utf-8"))
SINCE = "2026-11-01T00:00:00+00:00"
NOW = datetime.datetime(2026, 11, 7, 15, 0, tzinfo=datetime.timezone.utc)       # a Saturday afternoon
SUNDAY_EVENING = datetime.datetime(2026, 11, 8, 18, 30, tzinfo=datetime.timezone.utc)
SNAKE_FILE = "tattoo-preston-twisty-snake-flash-20261106.jpg"
PSALM_FILE = "tattoo-preston-psalm-23-script-20261103.jpg"


def photo_bytes(colour, size=(1500, 1200)):
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture
def fixture_images(tmp_path):
    d = tmp_path / "cdn"
    d.mkdir()
    (d / "a.jpg").write_bytes(photo_bytes((180, 40, 40)))
    (d / "b.jpg").write_bytes(photo_bytes((40, 180, 40)))
    (d / "c2.jpg").write_bytes(photo_bytes((40, 40, 180)))
    (d / "e.jpg").write_bytes(photo_bytes((120, 120, 120)))
    return d


class FakeApi:
    def __init__(self, media, images_dir, exists=None):
        self.media = media
        self.images_dir = images_dir
        self.exists = exists          # set of ids that still exist; None means all of them
        self.refresh_calls = 0

    def fetch_media(self, limit=25):
        return self.media

    def media_exists(self, media_id):
        return True if self.exists is None else media_id in self.exists

    def refresh(self):
        self.refresh_calls += 1
        return "NEWTOKEN", 5183944

    def download(self, url):
        return (self.images_dir / url.rsplit("/", 1)[-1]).read_bytes()


class Mailer:
    def __init__(self, configured=True):
        self.configured = configured
        self.sent = []

    def __call__(self, subject, body):
        if not self.configured:
            return False
        self.sent.append((subject, body))
        return True


def fresh_state(**extra):
    s = load_state(pathlib.Path("does-not-exist.json"))
    s["since"] = SINCE
    s.update(extra)
    return s


def page(repo, name):
    return (repo / "_src" / "pages" / name).read_text(encoding="utf-8")


def go(repo, images, media=None, state=None, now=NOW, dry_run=False, mailer=None, **kw):
    api = FakeApi(copy.deepcopy(media if media is not None else MEDIA), images, kw.pop("exists", None))
    state = state if state is not None else fresh_state()
    mailer = mailer if mailer is not None else Mailer()
    rep = run(repo, now, api, RULES, state, dry_run, mailer, **kw)
    return rep, state, mailer, api


def test_first_run_adds_two_photos(repo_copy, fixture_images):
    rep, state, mailer, _ = go(repo_copy, fixture_images)
    assert [c for _, c in rep.added] == [
        "Had a lot of fun doing this twisty snake from my flash, on the forearm",
        "Psalm 23 in script, forearm"]
    assert [f for f, _ in rep.added] == [SNAKE_FILE, PSALM_FILE]
    assert SNAKE_FILE in gallery_lines(page(repo_copy, "00-home.html"), "recent-h")[0]
    assert "Psalm 23" in page(repo_copy, "12-script-tattoos.html")
    assert "Psalm 23" in page(repo_copy, "13-christian-tattoos.html")
    assert "Psalm 23" not in page(repo_copy, "10-portrait-tattoos.html")
    assert (repo_copy / "images" / SNAKE_FILE).stat().st_size <= 400_000
    assert rep.rebuild and rep.changed
    assert rep.commit_message.startswith("Instagram: add ")
    assert [s for s, _ in mailer.sent] == [
        "Going on the site: Had a lot of fun doing this twisty snake from my flash, on the forearm",
        "Going on the site: Psalm 23 in script, forearm"]
    assert state["posts"]["a"]["status"] == "live" and state["posts"]["a"]["file"] == SNAKE_FILE
    assert state["posts"]["c"]["pages"] == ["12-script-tattoos.html", "13-christian-tattoos.html"]
    assert dict(rep.skipped) == {"b": "no line", "d": "video"}
    assert "b" not in state["posts"] and "d" not in state["posts"] and "e" not in state["posts"]


def test_dry_run_changes_nothing(repo_copy, fixture_images):
    before = page(repo_copy, "00-home.html")
    rep, state, mailer, _ = go(repo_copy, fixture_images, dry_run=True)
    assert len(rep.added) == 2 and not rep.changed and not rep.rebuild
    assert page(repo_copy, "00-home.html") == before
    assert not (repo_copy / "images" / SNAKE_FILE).exists()
    assert mailer.sent == [] and state["posts"] == {}


def test_second_run_is_quiet(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    rep, _, mailer, _ = go(repo_copy, fixture_images, state=state)
    assert rep.added == [] and rep.updated == [] and rep.removed == []
    assert not rep.changed and not rep.rebuild and mailer.sent == []


def test_caption_edit_updates_site(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    media = copy.deepcopy(MEDIA)
    media[0]["caption"] = "Twisty snake from my flash, on the forearm"
    rep, state, mailer, _ = go(repo_copy, fixture_images, media=media, state=state)
    assert rep.updated == [SNAKE_FILE] and rep.rebuild and rep.changed
    assert "| Twisty snake from my flash, on the forearm -->" in page(repo_copy, "00-home.html")
    assert state["posts"]["a"]["caption"] == "Twisty snake from my flash, on the forearm"
    assert mailer.sent == []


def test_line_removed_takes_photo_down(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    media = copy.deepcopy(MEDIA)
    media[0]["caption"] = "Had a lot of fun doing this twisty snake from my flash"
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state)
    assert rep.removed == [SNAKE_FILE] and rep.rebuild
    assert not (repo_copy / "images" / SNAKE_FILE).exists()
    assert SNAKE_FILE not in page(repo_copy, "00-home.html")
    assert SNAKE_FILE not in page(repo_copy, "15-walk-in-tattoos.html")
    assert state["posts"]["a"]["status"] == "removed"


def test_deleted_post_removed_on_existence_check(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    media = [m for m in MEDIA if m["id"] != "c"]
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state, exists={"a"}, existence_check=True)
    assert rep.removed == [PSALM_FILE]
    assert PSALM_FILE not in page(repo_copy, "12-script-tattoos.html")
    assert PSALM_FILE not in page(repo_copy, "13-christian-tattoos.html")
    assert not (repo_copy / "images" / PSALM_FILE).exists()
    assert state["posts"]["c"]["status"] == "removed"


def test_existence_check_is_skipped_outside_its_hour(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    media = [m for m in MEDIA if m["id"] != "c"]
    rep, _, _, _ = go(repo_copy, fixture_images, media=media, state=state, exists={"a"})
    assert rep.removed == []


def test_carousel_takes_first_image(repo_copy, fixture_images):
    go(repo_copy, fixture_images)
    expected = process_image((fixture_images / "c2.jpg").read_bytes())
    assert (repo_copy / "images" / PSALM_FILE).read_bytes() == expected


def test_token_refresh_after_seven_days(repo_copy, fixture_images):
    key = new_key()
    token_file = repo_copy / "_src" / "instagram" / "token.enc"
    token_file.parent.mkdir(parents=True)
    token_file.write_bytes(encrypt_token("OLD", key))
    state = fresh_state(token_refreshed="2026-10-30T15:00:00+00:00")
    _, state, _, api = go(repo_copy, fixture_images, state=state)   # first run: adds photos
    rep, state, _, api = go(repo_copy, fixture_images, state=state,
                            token="OLD", token_key=key, token_file=token_file)
    assert api.refresh_calls == 1
    assert decrypt_token(token_file.read_bytes(), key) == "NEWTOKEN"
    assert state["token_refreshed"] == "2026-11-07T15:00:00+00:00"
    assert state["token_expires"] == "2027-01-06T14:59:04+00:00"
    assert rep.changed and not rep.rebuild
    assert rep.commit_message == "Instagram: token refreshed"


def test_token_not_refreshed_when_fresh(repo_copy, fixture_images):
    key = new_key()
    token_file = repo_copy / "_src" / "instagram" / "token.enc"
    token_file.parent.mkdir(parents=True)
    token_file.write_bytes(encrypt_token("OLD", key))
    state = fresh_state(token_refreshed="2026-11-05T15:00:00+00:00")
    _, _, _, api = go(repo_copy, fixture_images, state=state, token="OLD", token_key=key, token_file=token_file)
    assert api.refresh_calls == 0


def test_digest_on_sunday_evening(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    rep, state, mailer, _ = go(repo_copy, fixture_images, state=state, now=SUNDAY_EVENING)
    assert [s for s, _ in mailer.sent] == ["Posts without a line this week"]
    assert "https://www.instagram.com/p/bbb/" in mailer.sent[0][1]
    assert "https://www.instagram.com/p/ddd/" not in mailer.sent[0][1]   # a video is never a candidate
    assert state["last_digest"] == "2026-11-08T18:30:00+00:00"
    # the next run that evening does not send it again
    rep, _, mailer, _ = go(repo_copy, fixture_images, state=state,
                           now=SUNDAY_EVENING + datetime.timedelta(hours=1))
    assert mailer.sent == []


def test_no_digest_on_a_weekday(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    _, _, mailer, _ = go(repo_copy, fixture_images, state=state, now=NOW)
    assert mailer.sent == []


def test_commit_message_joins_and_truncates():
    rep = Report()
    rep.added = [("a.jpg", "Twisty snake from my flash, on the forearm"),
                 ("b.jpg", "Psalm 23 in script, forearm"),
                 ("c.jpg", "Portrait of a dad and his baby, black and grey, inner forearm")]
    msg = commit_message(rep)
    assert msg.startswith("Instagram: add Twisty snake")
    assert len(msg) <= 72
    rep2 = Report()
    rep2.removed = ["old.jpg"]
    assert commit_message(rep2) == "Instagram: remove old.jpg"


def test_commit_message_for_a_digest_only_run():
    rep = Report()
    rep.notes = ["digest sent: 2 posts without a line"]
    assert commit_message(rep) == "Instagram: weekly digest sent"


def test_digest_run_has_a_commit_message(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    rep, _, _, _ = go(repo_copy, fixture_images, state=state, now=SUNDAY_EVENING)
    assert rep.changed and rep.commit_message == "Instagram: weekly digest sent"


def test_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    s = load_state(path)
    assert s["posts"] == {} and s["since"] is None
    s["since"] = SINCE
    s["posts"]["x"] = {"status": "live"}
    save_state(path, s)
    assert load_state(path) == s
    assert path.read_text(encoding="utf-8").endswith("}\n")


# Review findings, 7 Nov 2026: mail and network errors must not stop the site following Instagram,
# and an unconnected or lapsed connection must not fail every hour.

class RaisingMailer:
    def __call__(self, subject, body):
        raise RuntimeError("SMTP said no")


def test_mail_failure_does_not_stop_the_run(repo_copy, fixture_images):
    rep, state, _, _ = go(repo_copy, fixture_images, mailer=RaisingMailer())
    assert len(rep.added) == 2 and rep.changed and rep.rebuild
    assert (repo_copy / "images" / SNAKE_FILE).exists()
    assert state["posts"]["a"]["status"] == "live"
    assert any(n.startswith("mail failed") for n in rep.notes)


def test_digest_mail_failure_does_not_stop_the_run(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    rep, state, _, _ = go(repo_copy, fixture_images, state=state, now=SUNDAY_EVENING, mailer=RaisingMailer())
    assert any(n.startswith("mail failed") for n in rep.notes)
    assert state["last_digest"] is None


class FlakyApi(FakeApi):
    def media_exists(self, media_id):
        raise OSError("timed out")


def test_network_error_in_existence_check_leaves_posts_alone(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    api = FlakyApi([m for m in MEDIA if m["id"] != "c"], fixture_images)
    rep = run(repo_copy, NOW, api, RULES, state, False, Mailer(), existence_check=True)
    assert rep.removed == [] and state["posts"]["c"]["status"] == "live"
    assert any("could not check" in n for n in rep.notes)


class AuthFailingApi(FakeApi):
    def media_exists(self, media_id):
        from api import ApiError
        raise ApiError("bad token", code=190)


def test_auth_error_in_existence_check_still_raises(repo_copy, fixture_images):
    from api import ApiError
    _, state, _, _ = go(repo_copy, fixture_images)
    api = AuthFailingApi([m for m in MEDIA if m["id"] != "c"], fixture_images)
    with pytest.raises(ApiError):
        run(repo_copy, NOW, api, RULES, state, False, Mailer(), existence_check=True)


def main_in(tmp_path, monkeypatch, *, since=None, now="2026-11-07T15:00:00+00:00"):
    import sync
    sent = []
    monkeypatch.setattr(sync, "TOKEN_FILE", tmp_path / "token.enc")
    monkeypatch.setattr(sync, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(sync.mail, "send", lambda subject, body, env=None: sent.append(subject) or True)
    monkeypatch.delenv("IG_TOKEN_KEY", raising=False)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    if since:
        save_state(tmp_path / "state.json", {**load_state(None), "since": since})
    return sync.main(["--repo", str(tmp_path), "--now", now]), sent


def test_not_connected_yet_is_quiet(tmp_path, monkeypatch, capsys):
    code, sent = main_in(tmp_path, monkeypatch)
    assert code == 0 and sent == []
    assert "Not connected yet" in capsys.readouterr().out


def test_lapsed_connection_is_loud_once_a_day(tmp_path, monkeypatch, capsys):
    code, sent = main_in(tmp_path, monkeypatch, since=SINCE, now="2026-11-07T08:30:00+00:00")
    assert code == 2 and sent == ["The site has stopped following Instagram"]
    assert "setting up again" in capsys.readouterr().out


def test_lapsed_connection_is_quiet_at_other_hours(tmp_path, monkeypatch, capsys):
    code, sent = main_in(tmp_path, monkeypatch, since=SINCE, now="2026-11-07T15:00:00+00:00")
    assert code == 0 and sent == []
    assert "setting up again" in capsys.readouterr().out


def test_cli_dry_run_against_fixture(repo_copy, fixture_images):
    r = subprocess.run(
        [sys.executable, "-I", str(HERE.parent / "sync.py"), "--dry-run",
         "--fixture", str(HERE / "fixtures" / "media.json"), "--images", str(fixture_images),
         "--repo", str(repo_copy), "--since", SINCE, "--now", "2026-11-07T15:00:00+00:00"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "would add" in r.stdout and SNAKE_FILE in r.stdout and "no line" in r.stdout
    assert not (repo_copy / "images" / SNAKE_FILE).exists()
