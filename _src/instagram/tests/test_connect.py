"""The one-off connection: Caitlin's allow tap becomes an encrypted token file and one secret."""
import datetime
import json
from urllib.parse import quote

import pytest

from connect import REDIRECT_URI, authorize_url, clean_code, exchange, store
from state import load_state
from tokenstore import decrypt_token

NOW = datetime.datetime(2026, 11, 7, 16, 0, tzinfo=datetime.timezone.utc)


def test_redirect_uri():
    assert REDIRECT_URI == "https://caitlincarneytattoo.co.uk/instagram-connect/"


def test_authorize_url():
    url = authorize_url("123")
    assert url.startswith("https://www.instagram.com/oauth/authorize?")
    assert "client_id=123" in url
    assert "redirect_uri=" + quote(REDIRECT_URI, safe="") in url
    assert "response_type=code" in url
    assert "scope=instagram_business_basic" in url


def test_clean_code():
    assert clean_code(" abc#_ ") == "abc"
    assert clean_code("https://caitlincarneytattoo.co.uk/instagram-connect/?code=XYZ#_") == "XYZ"
    assert clean_code("https://caitlincarneytattoo.co.uk/instagram-connect/?code=XYZ&state=1") == "XYZ"


def test_exchange():
    calls = []

    def http(url, data=None):
        calls.append((url, data))
        if data is not None:
            return json.dumps({"data": [{"access_token": "SHORT", "user_id": 1,
                                         "permissions": "instagram_business_basic"}]}).encode()
        return json.dumps({"access_token": "LONG", "token_type": "bearer", "expires_in": 5183944}).encode()

    assert exchange("123", "sec", "XYZ", http=http) == ("LONG", 5183944)
    post_url, post_body = calls[0]
    assert post_url == "https://api.instagram.com/oauth/access_token"
    assert b"grant_type=authorization_code" in post_body and b"code=XYZ" in post_body
    assert b"client_secret=sec" in post_body and b"client_id=123" in post_body
    get_url, get_body = calls[1]
    assert get_body is None
    assert get_url.startswith("https://graph.instagram.com/access_token?")
    assert "grant_type=ig_exchange_token" in get_url and "access_token=SHORT" in get_url
    assert "client_secret=sec" in get_url


def test_exchange_accepts_flat_shape():
    def http(url, data=None):
        if data is not None:
            return json.dumps({"access_token": "SHORT", "user_id": 1}).encode()
        return json.dumps({"access_token": "LONG", "expires_in": 100}).encode()

    assert exchange("123", "sec", "XYZ", http=http) == ("LONG", 100)


def test_check_gh_refuses_when_gh_is_missing_or_signed_out(monkeypatch):
    import subprocess
    import connect

    def failing_run(*a, **kw):
        raise subprocess.CalledProcessError(1, a[0])
    monkeypatch.setattr(connect.subprocess, "run", failing_run)
    with pytest.raises(SystemExit, match="gh auth login"):
        connect.check_gh()


def test_gh_is_checked_before_the_code_is_asked_for(monkeypatch):
    """A used code cannot be used again, so gh must be known good before the exchange."""
    import connect
    answers = iter(["123"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(connect, "check_gh", lambda: (_ for _ in ()).throw(SystemExit("gh auth login")))
    monkeypatch.setattr(connect, "exchange", lambda *a, **k: pytest.fail("exchange must not run"))
    with pytest.raises(SystemExit):
        connect.main([])


def test_prompts_name_the_instagram_app_id(monkeypatch, capsys):
    import connect
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt="": prompts.append(prompt) or "123")
    connect.main(["--link"])
    assert "Instagram app ID" in prompts[0] and "Meta app ID" in prompts[0]
    assert authorize_url("123") in capsys.readouterr().out


def test_store(tmp_path):
    secrets = []
    store("LONG", 5183944, NOW, tmp_path, lambda name, value: secrets.append((name, value)))
    assert len(secrets) == 1 and secrets[0][0] == "IG_TOKEN_KEY" and len(secrets[0][1]) == 44
    key = secrets[0][1]
    token_file = tmp_path / "_src" / "instagram" / "token.enc"
    assert decrypt_token(token_file.read_bytes(), key) == "LONG"
    assert b"LONG" not in token_file.read_bytes()
    state = load_state(tmp_path / "_src" / "instagram" / "state.json")
    assert state["since"] == "2026-11-07T16:00:00+00:00"
    assert state["token_refreshed"] == "2026-11-07T16:00:00+00:00"
    assert state["token_expires"] == "2027-01-06T15:59:04+00:00"
    assert state["posts"] == {}
