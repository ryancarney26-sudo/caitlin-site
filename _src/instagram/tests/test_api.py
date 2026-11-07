"""The Instagram API client, against a fake urlopen that records what was asked for."""
import datetime
import io
import json
import urllib.error

import pytest

import api
from api import Api, ApiError, GRAPH, parse_timestamp


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake(monkeypatch, *, status=200, body=b"{}"):
    """Install a fake urlopen that returns `body` (or raises HTTPError for status >= 400)
    and records every URL it was given."""
    calls = []

    def urlopen(url, timeout=None):
        calls.append(url)
        if status >= 400:
            raise urllib.error.HTTPError(url, status, "error", {}, io.BytesIO(body))
        return FakeResponse(body)

    monkeypatch.setattr(api, "urlopen", urlopen)
    return calls


def jbody(obj):
    return json.dumps(obj).encode("utf-8")


def test_fetch_media_asks_for_fields_and_returns_data(monkeypatch):
    calls = fake(monkeypatch, body=jbody({"data": [{"id": "1"}], "paging": {}}))
    assert Api("TOK").fetch_media() == [{"id": "1"}]
    url = calls[0]
    assert url.startswith(GRAPH + "/me/media?")
    assert "fields=id%2Ccaption%2Cmedia_type" in url and "limit=25" in url and "access_token=TOK" in url


def test_media_exists_true(monkeypatch):
    fake(monkeypatch, body=jbody({"id": "17"}))
    assert Api("TOK").media_exists("17") is True


def test_media_exists_false_when_deleted(monkeypatch):
    fake(monkeypatch, status=400, body=jbody({"error": {
        "message": "Unsupported get request. Object with ID '17' does not exist, cannot be loaded due to missing permissions, or does not support this operation",
        "type": "GraphMethodException", "code": 100, "error_subcode": 33}}))
    assert Api("TOK").media_exists("17") is False


def test_media_exists_raises_on_other_errors(monkeypatch):
    fake(monkeypatch, status=500, body=jbody({"error": {"message": "server", "code": 2}}))
    with pytest.raises(ApiError) as e:
        Api("TOK").media_exists("17")
    assert not e.value.is_auth


def test_auth_error_is_flagged(monkeypatch):
    fake(monkeypatch, status=400, body=jbody({"error": {
        "message": "Invalid OAuth access token", "type": "OAuthException", "code": 190}}))
    with pytest.raises(ApiError) as e:
        Api("TOK").fetch_media()
    assert e.value.is_auth and e.value.code == 190


def test_refresh(monkeypatch):
    calls = fake(monkeypatch, body=jbody({"access_token": "NEW", "token_type": "bearer", "expires_in": 5183944}))
    assert Api("OLD").refresh() == ("NEW", 5183944)
    assert "refresh_access_token?" in calls[0] and "grant_type=ig_refresh_token" in calls[0] and "access_token=OLD" in calls[0]


def test_download(monkeypatch):
    fake(monkeypatch, body=b"\xff\xd8\xff\xe0JFIF")
    assert Api("TOK").download("https://cdn.example/photo.jpg") == b"\xff\xd8\xff\xe0JFIF"


def test_parse_timestamp():
    assert parse_timestamp("2026-11-06T18:21:05+0000") == datetime.datetime(
        2026, 11, 6, 18, 21, 5, tzinfo=datetime.timezone.utc)
