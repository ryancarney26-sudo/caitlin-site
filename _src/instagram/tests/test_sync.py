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
    (d / "f.jpg").write_bytes(photo_bytes((150, 90, 60)))
    (d / "g.jpg").write_bytes(photo_bytes((60, 90, 150)))
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


def test_every_new_photo_also_joins_all_my_tattoos(repo_copy, fixture_images):
    go(repo_copy, fixture_images)
    archive = page(repo_copy, "17-tattoos.html")
    assert SNAKE_FILE in gallery_lines(archive, "photos-h")[0]
    assert PSALM_FILE in archive


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


def test_taking_her_line_out_without_claude_keeps_the_photo(repo_copy, fixture_images):
    """Since 7 Nov every photo post belongs on the site, so a line taken out no longer takes it down."""
    _, state, _, _ = go(repo_copy, fixture_images)
    media = copy.deepcopy(MEDIA)
    media[0]["caption"] = "Had a lot of fun doing this twisty snake from my flash"
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state)
    assert rep.removed == [] and rep.updated == []
    assert (repo_copy / "images" / SNAKE_FILE).exists()
    assert "| Had a lot of fun doing this twisty snake from my flash, on the forearm -->" in page(repo_copy, "00-home.html")
    assert state["posts"]["a"]["status"] == "live"


def test_deleted_post_removed_on_existence_check(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    media = [m for m in MEDIA if m["id"] != "c"]
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state, exists={"a"}, existence_check=True)
    assert rep.removed == [PSALM_FILE]
    assert PSALM_FILE not in page(repo_copy, "12-script-tattoos.html")
    assert PSALM_FILE not in page(repo_copy, "13-christian-tattoos.html")
    assert not (repo_copy / "images" / PSALM_FILE).exists()
    assert state["posts"]["c"]["status"] == "removed"


def test_existence_check_runs_on_every_daily_run(repo_copy, fixture_images):
    """8 Nov 2026: the robot runs once a day, so every run checks for deleted posts."""
    _, state, _, _ = go(repo_copy, fixture_images)
    media = [m for m in MEDIA if m["id"] != "c"]
    rep, _, _, _ = go(repo_copy, fixture_images, media=media, state=state, exists={"a"})
    assert rep.removed == [PSALM_FILE]


def test_digest_on_a_sunday_at_any_hour(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    sunday_morning = datetime.datetime(2026, 11, 8, 7, 23, tzinfo=datetime.timezone.utc)
    _, _, mailer, _ = go(repo_copy, fixture_images, state=state, now=sunday_morning)
    assert [s for s, _ in mailer.sent] == ["Kept off the site this week"]


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
    assert [s for s, _ in mailer.sent] == ["Kept off the site this week"]
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


def main_in(tmp_path, monkeypatch, *, since=None, now="2026-11-07T15:00:00+00:00", output=None):
    import sync
    sent = []
    monkeypatch.setattr(sync, "TOKEN_FILE", tmp_path / "token.enc")
    monkeypatch.setattr(sync, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(sync.mail, "send", lambda subject, body, env=None: sent.append(subject) or True)
    monkeypatch.delenv("IG_TOKEN_KEY", raising=False)
    if output:
        monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    else:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    if since:
        save_state(tmp_path / "state.json", {**load_state(None), "since": since})
    return sync.main(["--repo", str(tmp_path), "--now", now]), sent


def test_not_connected_yet_is_quiet(tmp_path, monkeypatch, capsys):
    code, sent = main_in(tmp_path, monkeypatch)
    assert code == 0 and sent == []
    assert "Not connected yet" in capsys.readouterr().out


def test_lapsed_connection_is_reported_at_any_hour(tmp_path, monkeypatch, capsys):
    code, sent = main_in(tmp_path, monkeypatch, since=SINCE, now="2026-11-07T19:23:00+00:00")
    assert code == 2 and sent == ["The site has stopped following Instagram"]
    assert "setting up again" in capsys.readouterr().out


def test_lapsed_connection_is_reported_once_a_day(tmp_path, monkeypatch, capsys):
    """The evening run speaks up; its backup tries the same evening stay quiet; the next evening speaks again."""
    import sync
    code, sent = main_in(tmp_path, monkeypatch, since=SINCE, now="2026-11-07T19:23:00+00:00")
    assert code == 2 and len(sent) == 1
    assert load_state(tmp_path / "state.json")["last_alert"] == "2026-11-07T19:23:00+00:00"
    assert sync.main(["--repo", str(tmp_path), "--now", "2026-11-07T21:23:00+00:00"]) == 0
    assert len(sent) == 1
    assert "setting up again" in capsys.readouterr().out
    assert sync.main(["--repo", str(tmp_path), "--now", "2026-11-08T19:23:00+00:00"]) == 2
    assert len(sent) == 2


def test_a_lapse_warning_is_committed_so_the_backups_know(tmp_path, monkeypatch):
    out = tmp_path / "github_output"
    main_in(tmp_path, monkeypatch, since=SINCE, now="2026-11-07T19:23:00+00:00", output=out)
    text = out.read_text(encoding="utf-8")
    assert "changed=true" in text and "rebuild=false" in text
    assert "message=Instagram: connection warning sent" in text


# 7 Nov 2026, Ryan: "all new posts should be uploaded". Claude looks at each photo post that has no
# line of hers: a finished tattoo goes up with Claude's plain caption, anything else is kept off.

from describe import DescribeError, Description  # noqa: E402

F = {"id": "f", "caption": "So happy with how this one healed 🖤", "media_type": "IMAGE",
     "media_url": "https://cdn.example/f.jpg", "permalink": "https://www.instagram.com/p/fff/",
     "timestamp": "2026-11-05T12:00:00+0000"}
G = {"id": "g", "caption": "New flash sheet up for this week's walk-ins", "media_type": "IMAGE",
     "media_url": "https://cdn.example/g.jpg", "permalink": "https://www.instagram.com/p/ggg/",
     "timestamp": "2026-11-05T13:00:00+0000"}
MEDIA2 = [MEDIA[0], G, F] + MEDIA[1:]
ROSE = "Black and grey rose tattoo on the shoulder"
ANSWERS = {
    F["caption"]: Description(True, ROSE, ["small"]),
    G["caption"]: Description(False, "", []),
    MEDIA[1]["caption"]: Description(False, "", []),        # the colour realism offer
}


class FakeDescriber:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, jpeg, caption):
        self.calls.append(caption)
        answer = self.answers[caption]
        if isinstance(answer, Exception):
            raise answer
        return answer


def rose_file(state):
    return state["posts"]["f"]["file"]


def test_claude_captions_photo_posts_without_her_line(repo_copy, fixture_images):
    describer = FakeDescriber(ANSWERS)
    rep, state, mailer, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=describer)
    assert sorted(describer.calls) == sorted([F["caption"], G["caption"], MEDIA[1]["caption"]])
    assert ROSE in [caption for _, caption in rep.added]
    f = state["posts"]["f"]
    assert (f["status"], f["source"], f["pages"]) == ("live", "claude", ["15-walk-in-tattoos.html"])
    assert state["posts"]["a"]["source"] == "hers"
    assert state["posts"]["g"] == {"status": "skipped", "reason": "not a tattoo",
                                   "permalink": G["permalink"], "timestamp": G["timestamp"]}
    assert state["posts"]["b"]["reason"] == "not a tattoo"
    assert ROSE in page(repo_copy, "00-home.html") and ROSE in page(repo_copy, "15-walk-in-tattoos.html")
    rose_mail = next(body for subject, body in mailer.sent if subject == f"Going on the site: {ROSE}")
    assert "Claude wrote this caption" in rose_mail


def test_kept_off_posts_are_not_asked_about_again(repo_copy, fixture_images):
    describer = FakeDescriber(ANSWERS)
    _, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=describer)
    rep, _, _, _ = go(repo_copy, fixture_images, media=MEDIA2, state=state, describer=describer)
    assert len(describer.calls) == 3
    assert not rep.changed


def test_her_line_replaces_claudes_caption(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=FakeDescriber(ANSWERS))
    media = copy.deepcopy(MEDIA2)
    media[2]["caption"] = "Rose from my flash, on the shoulder"
    describer = FakeDescriber(ANSWERS)
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state, describer=describer)
    assert rep.updated == [rose_file(state)] and describer.calls == []
    assert (state["posts"]["f"]["caption"], state["posts"]["f"]["source"]) == ("Rose from my flash, on the shoulder", "hers")
    assert "| Rose from my flash, on the shoulder -->" in page(repo_copy, "00-home.html")


def test_taking_her_line_out_lets_claude_caption_it(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images)
    media = copy.deepcopy(MEDIA)
    no_line = "Had a lot of fun doing this twisty snake from my flash"
    media[0]["caption"] = no_line
    snake = "Black and grey snake tattoo on the forearm"
    describer = FakeDescriber({no_line: Description(True, snake, ["small"]),
                               MEDIA[1]["caption"]: Description(False, "", [])})
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state, describer=describer)
    assert rep.updated == [SNAKE_FILE] and rep.removed == []
    assert (state["posts"]["a"]["caption"], state["posts"]["a"]["source"]) == (snake, "claude")
    assert f"| {snake} -->" in page(repo_copy, "00-home.html")
    assert (repo_copy / "images" / SNAKE_FILE).exists()


NO_LINE = "Had a lot of fun doing this twisty snake from my flash"


def line_taken_out(repo_copy, fixture_images, answer):
    """Run 1 puts the snake up with her line; run 2 sees the line gone and asks Claude."""
    _, state, _, _ = go(repo_copy, fixture_images)
    media = copy.deepcopy(MEDIA)
    media[0]["caption"] = NO_LINE
    describer = FakeDescriber({NO_LINE: answer, MEDIA[1]["caption"]: Description(False, "", [])})
    rep, state, _, _ = go(repo_copy, fixture_images, media=media, state=state, describer=describer)
    return rep, state, describer, media


def test_line_out_and_claude_sees_no_tattoo_keeps_her_caption_and_asks_once(repo_copy, fixture_images):
    rep, state, describer, media = line_taken_out(repo_copy, fixture_images, Description(False, "", []))
    assert state["posts"]["a"]["status"] == "live" and SNAKE_FILE in page(repo_copy, "00-home.html")
    assert rep.changed and rep.commit_message.startswith("Instagram: ")
    _, _, _, _ = go(repo_copy, fixture_images, media=media, state=state, describer=describer)
    assert describer.calls.count(NO_LINE) == 1


def test_line_out_and_claude_fails_for_good_keeps_the_photo_live(repo_copy, fixture_images):
    rep, state, describer, media = line_taken_out(repo_copy, fixture_images,
                                                  DescribeError("answer cut off", retry=False))
    assert state["posts"]["a"]["status"] == "live"
    assert SNAKE_FILE in page(repo_copy, "00-home.html") and (repo_copy / "images" / SNAKE_FILE).exists()
    _, _, _, _ = go(repo_copy, fixture_images, media=media, state=state, describer=describer)
    assert describer.calls.count(NO_LINE) == 1


def test_claude_trouble_is_tried_again_next_hour(repo_copy, fixture_images):
    busy = FakeDescriber({**ANSWERS, F["caption"]: DescribeError("overloaded", retry=True)})
    rep, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=busy)
    assert "f" not in state["posts"]
    assert any(pid == "f" and reason.startswith("Claude") for pid, reason in rep.skipped)
    rep, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, state=state, describer=FakeDescriber(ANSWERS))
    assert state["posts"]["f"]["status"] == "live"


def test_a_bad_key_stops_claude_for_the_run(repo_copy, fixture_images):
    refused = DescribeError("HTTP 401", retry=True, stop_all=True)
    describer = FakeDescriber({key: refused for key in ANSWERS})
    rep, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=describer)
    assert len(describer.calls) == 1
    assert not any(pid in state["posts"] for pid in ("b", "f", "g"))
    assert any("Claude" in note for note in rep.notes)


def test_claude_is_asked_at_most_n_times_a_run(repo_copy, fixture_images):
    rules = {**RULES, "max_claude_per_run": 1}
    describer = FakeDescriber(ANSWERS)
    state = fresh_state()
    rep = run(repo_copy, NOW, FakeApi(copy.deepcopy(MEDIA2), fixture_images), rules, state, False, Mailer(),
              describer=describer)
    assert len(describer.calls) == 1
    assert sum(reason == "waiting for Claude" for _, reason in rep.skipped) == 2


def test_a_final_claude_failure_is_remembered(repo_copy, fixture_images):
    cut_off = FakeDescriber({**ANSWERS, F["caption"]: DescribeError("answer cut off", retry=False)})
    _, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=cut_off)
    assert state["posts"]["f"]["status"] == "skipped" and "answer cut off" in state["posts"]["f"]["reason"]
    _, _, _, _ = go(repo_copy, fixture_images, media=MEDIA2, state=state, describer=cut_off)
    assert cut_off.calls.count(F["caption"]) == 1


def test_a_name_claude_copies_from_a_tattoo_reaches_no_page_record_or_message(repo_copy, fixture_images):
    """The whole path, with describe.py's own check and no stand-in for it. Claude lists the name it
    can read in the tattoo, then slips and writes it into the caption. The photo stays off, and the
    name is in no page, no record in state.json, no skip reason, no commit message and no email."""
    from types import SimpleNamespace

    from describe import parse_response

    slipped = {"finished_tattoo": True, "private_details": ["Olivia"],
               "caption": "Script tattoo of the name Olivia on the wrist", "kinds": ["script"]}
    no_tattoo = {"finished_tattoo": False, "private_details": [], "caption": "", "kinds": []}
    answers = {F["caption"]: slipped, G["caption"]: no_tattoo, MEDIA[1]["caption"]: no_tattoo}

    def describer(jpeg, caption):
        text = SimpleNamespace(type="text", text=json.dumps(answers[caption]))
        return parse_response(SimpleNamespace(stop_reason="end_turn", content=[text]))

    rep, state, mailer, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=describer)
    assert state["posts"]["f"]["status"] == "skipped"
    pages = "".join(p.read_text(encoding="utf-8") for p in (repo_copy / "_src" / "pages").glob("*.html"))
    public = pages + json.dumps(state) + repr(rep.skipped) + repr(rep.notes) + rep.commit_message + repr(mailer.sent)
    assert "Olivia" not in public
    _, _, mailer, _ = go(repo_copy, fixture_images, media=MEDIA2, state=state, now=SUNDAY_EVENING, describer=describer)
    assert F["permalink"] in mailer.sent[-1][1] and "Olivia" not in repr(mailer.sent)     # Sunday's list names the post, not the name


def test_kept_off_posts_are_in_the_sunday_list(repo_copy, fixture_images):
    _, state, _, _ = go(repo_copy, fixture_images, media=MEDIA2, describer=FakeDescriber(ANSWERS))
    _, state, mailer, _ = go(repo_copy, fixture_images, media=MEDIA2, state=state, now=SUNDAY_EVENING,
                             describer=FakeDescriber(ANSWERS))
    subject, body = mailer.sent[-1]
    assert subject == "Kept off the site this week"
    assert G["permalink"] in body and "add one line" in body
    assert F["permalink"] not in body                      # the rose went up


def test_a_run_that_only_keeps_posts_off_has_a_commit_message(repo_copy, fixture_images):
    describer = FakeDescriber({G["caption"]: Description(False, "", []),
                               MEDIA[1]["caption"]: Description(False, "", [])})
    _, state, _, _ = go(repo_copy, fixture_images)            # a and c up, with her lines
    rep, _, _, _ = go(repo_copy, fixture_images, media=[G] + MEDIA, state=state, describer=describer)
    assert rep.changed and not rep.rebuild
    assert rep.commit_message == "Instagram: kept off 2 posts"


def test_claude_is_used_only_when_its_key_is_set(monkeypatch):
    import sync
    monkeypatch.setattr(sync, "make_describer", lambda key: ("describer for", key))
    assert sync.describer_from_env({}) is None
    assert sync.describer_from_env({"ANTHROPIC_API_KEY": "  "}) is None
    assert sync.describer_from_env({"ANTHROPIC_API_KEY": "k"}) == ("describer for", "k")


def test_commit_message_for_one_post_kept_off():
    rep = Report()
    rep.kept_off = ["g"]
    assert commit_message(rep) == "Instagram: kept off 1 post"


def test_cli_dry_run_against_fixture(repo_copy, fixture_images):
    r = subprocess.run(
        [sys.executable, "-I", str(HERE.parent / "sync.py"), "--dry-run",
         "--fixture", str(HERE / "fixtures" / "media.json"), "--images", str(fixture_images),
         "--repo", str(repo_copy), "--since", SINCE, "--now", "2026-11-07T15:00:00+00:00"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "would add" in r.stdout and SNAKE_FILE in r.stdout and "no line" in r.stdout
    assert not (repo_copy / "images" / SNAKE_FILE).exists()
