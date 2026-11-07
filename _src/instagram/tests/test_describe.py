"""Claude looks at one photo: is it a finished tattoo, and what plain line describes it."""
import base64
import json
from types import SimpleNamespace

import pytest

import describe
from describe import (FALLBACK_BETA, MODEL, SCHEMA, Description, DescribeError, build_request,
                      error_for_status, pages_for_kinds, parse_response)

JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HER_CAPTION = "Had a lot of fun doing this twisty snake from my flash 😝🐍"


def reply(payload, stop_reason="end_turn"):
    """A response shaped like the SDK's: a thinking block, then the JSON text block."""
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(stop_reason=stop_reason, content=[
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text=text),
    ])


TATTOO = {"finished_tattoo": True, "caption": "Black and grey snake tattoo on the forearm", "kinds": ["small"]}


def test_request_shape():
    req = build_request(JPEG, HER_CAPTION)
    assert req["model"] == MODEL == "claude-opus-5-5"
    assert req["betas"] == [FALLBACK_BETA] and req["fallbacks"] == "default"
    assert req["output_config"]["effort"] == "low"
    assert req["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    assert SCHEMA["additionalProperties"] is False
    image, text = req["messages"][0]["content"]
    assert image["type"] == "image"
    assert image["source"] == {"type": "base64", "media_type": "image/jpeg",
                               "data": base64.standard_b64encode(JPEG).decode("ascii")}
    assert HER_CAPTION in text["text"]
    assert "finished tattoo" in req["system"]


def test_request_without_her_caption():
    text = build_request(JPEG, None)["messages"][0]["content"][1]["text"]
    assert "no caption" in text


def test_parse_a_tattoo():
    assert parse_response(reply(TATTOO)) == Description(True, "Black and grey snake tattoo on the forearm", ["small"])


def test_parse_tidies_the_caption():
    d = parse_response(reply({**TATTOO, "caption": "  black and grey snake tattoo on the forearm. "}))
    assert d.caption == "Black and grey snake tattoo on the forearm"


def test_parse_not_a_tattoo_needs_no_caption():
    assert parse_response(reply({"finished_tattoo": False, "caption": "", "kinds": []})) == Description(False, "", [])


@pytest.mark.parametrize("caption", [
    "Snake tattoo on the forearm #tattoo",
    "Snake tattoo for @someone on the forearm",
    " ".join(["word"] * 21),
    "Snake",
])
def test_parse_rejects_a_bad_caption_for_good(caption):
    with pytest.raises(DescribeError) as e:
        parse_response(reply({**TATTOO, "caption": caption}))
    assert not e.value.retry


def test_parse_refusal_is_final():
    with pytest.raises(DescribeError) as e:
        parse_response(reply(TATTOO, stop_reason="refusal"))
    assert not e.value.retry


def test_parse_cut_off_answer_is_final():
    with pytest.raises(DescribeError) as e:
        parse_response(reply('{"finished_tattoo": true, "capt', stop_reason="max_tokens"))
    assert not e.value.retry


def test_pages_for_kinds():
    assert pages_for_kinds(["portrait", "christian"]) == ["10-portrait-tattoos.html", "13-christian-tattoos.html"]
    assert pages_for_kinds(["small", "nonsense"]) == ["15-walk-in-tattoos.html"]
    assert pages_for_kinds([]) == []


def test_describe_sends_the_request_and_reads_the_answer():
    calls = []
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
        create=lambda **kw: calls.append(kw) or reply(TATTOO))))
    assert describe.describe(client, JPEG, HER_CAPTION).caption == "Black and grey snake tattoo on the forearm"
    assert calls[0]["model"] == MODEL


@pytest.mark.parametrize("status,retry,stop_all", [
    (None, True, False),     # no answer at all: the network
    (429, True, False),      # busy
    (529, True, False),      # overloaded
    (500, True, False),
    (401, True, True),       # the key is wrong: stop asking this run, try again next hour
    (403, True, True),
    (400, True, True),       # a request this code built badly: never mark posts for good
])
def test_error_for_status(status, retry, stop_all):
    e = error_for_status(status, "boom")
    assert (e.retry, e.stop_all) == (retry, stop_all)
