"""Claude looks at one photo: is it a finished tattoo, and what plain line describes it."""
import base64
import dataclasses
import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image

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


TATTOO = {"finished_tattoo": True, "private_details": [], "caption": "Black and grey snake tattoo on the forearm",
          "kinds": ["small"]}


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
    not_a_tattoo = {"finished_tattoo": False, "private_details": [], "caption": "", "kinds": []}
    assert parse_response(reply(not_a_tattoo)) == Description(False, "", [])


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


@pytest.mark.parametrize("caption,secret", [
    ("Script tattoo of the name Olivia " + " ".join(["word"] * 20), "Olivia"),     # too long
    ("Olivia script", "Olivia"),                                                  # too short
    ("Snake tattoo for Olivia #tattoo", "Olivia"),                                # breaks the hashtag rule
])
def test_a_rejected_caption_is_never_quoted_in_the_reason(caption, secret):
    """The reason is stored in state.json and printed in the run log, and the repository is public.
    A rejected caption may be the very one that spells out a client's name."""
    with pytest.raises(DescribeError) as e:
        parse_response(reply({**TATTOO, "caption": caption}))
    assert secret not in str(e.value)


def test_the_instructions_keep_a_name_a_date_and_a_birth_weight_out_of_the_caption():
    """A name, a date or a birth weight in a tattoo belongs to the person wearing it, and a caption
    is public text. So Claude is told to say "a name" or "a date" and never to copy the real one."""
    system = build_request(JPEG, None)["system"]
    assert "Never copy it into the caption" in system
    assert all(phrase in system for phrase in ('"a name"', '"a date"', '"a birth weight"'))


def test_the_instructions_ask_for_no_religious_wording_of_claudes_own():
    assert "Add no religious wording of your own" in build_request(JPEG, None)["system"]


# The check under that instruction: ask, don't guess. Claude lists the private details it can read
# in the tattoo, and a caption that holds any of them keeps the photo off. Nothing is reworded.

def test_claude_is_asked_to_list_the_private_details_it_can_read():
    assert SCHEMA["properties"]["private_details"] == {"type": "array", "items": {"type": "string"}}
    assert "private_details" in SCHEMA["required"]
    system = build_request(JPEG, None)["system"]
    for sentence in ("Put each such name, date and birth weight in private_details",
                     "with no other word around it",
                     "Whatever you list must stay out of the caption",
                     "Mum, Dad and Nan are not names",
                     "list it twice",
                     "That list is never published"):
        assert sentence in system, sentence


def test_the_private_list_comes_before_the_caption_in_the_answer():
    """Listing them first puts them in front of Claude before it writes the line that must not hold them."""
    asked = list(SCHEMA["properties"])
    assert asked.index("private_details") < asked.index("caption")


@pytest.mark.parametrize("caption,private", [
    ("Script tattoo of the name Olivia on the wrist", ["Olivia"]),
    ("Script tattoo of the name Olivia on the wrist", ["OLIVIA"]),                 # in capitals in the tattoo
    ("Script tattoo of the name Olivia on the wrist", ["olivia"]),                 # in lower-case script
    ("Olivia's name in script on the wrist, black and grey", ["Olivia"]),
    ("Script tattoo reading Olivia, fine line, on the wrist", ["Olivia"]),         # no word "name" at all
    ("Script tattoo of the name Zoe on the wrist", ["Zoë"]),                       # the accent dropped
    ("Script tattoo of the names Ava and Noah on the forearm", ["Ava", "Noah"]),
    ("Script tattoo reading Noah on the forearm", ["Ava and Noah"]),               # two names given as one item
    ("Rose tattoo with the name Mary-Jane on the hand", ["Mary Jane O'Neil"]),
    ("Script tattoo of the surname O'Neil across the back", ["Mary-Jane O'Neil"]),
    ("Cross tattoo with the date 12.03.2019, black and grey", ["12.03.2019"]),
    ("Cross tattoo with the date 12 03 2019, black and grey", ["12.03.2019"]),     # other marks between the parts
    ("Cross tattoo with the date 12/03/2019, black and grey", ["12.03.2019"]),
    ("Cross tattoo dated 12 March 2019, black and grey", ["12.03.2019"]),          # reworded, the year still there
    ("Memorial script tattoo, Dad 1950 to 2020, on the forearm", ["1950 - 2020"]),
    ("Script tattoo with the date XII III MMXIX on the ribs", ["XII.III.MMXIX"]),
    ("Baby footprint tattoo with a name, 7lb 6oz and a heart", ["7lb6oz"]),
    ("Baby footprint tattoo with a name, 7 lb 6 oz and a heart", ["7lb 6oz"]),
    ("Baby footprint tattoo with a name, 7-6 and a heart", ["7-6"]),               # a weight in two figures
    ("Baby footprint tattoo with a name, 7.6 and a heart", ["7-6"]),
    # what the review of 10 Nov 2026 found getting through
    ("Script tattoo of the date 12.03.19, 3 small stars and a heart", ["12.03.19"]),      # a figure next door
    ("Baby footprint tattoo with a name, 12.03.19, 7lb 6oz, black and grey", ["12.03.19"]),
    ("Baby footprint tattoo with a name, 12.03.19, 7lb 6oz, black and grey", ["7lb 6oz"]),
    ("Memorial script tattoo with the dates 12.03.50 - 04.07.21 on the forearm", ["04.07.21"]),
    ("Baby footprints tattoo with a name, 7lb 6oz, 52cm, black and grey", ["7lb 6oz"]),
    ("Baby footprint tattoo with a name, 7lbs 6oz and a heart", ["7lb 6oz"]),             # the unit spelled another way
    ("Baby footprint tattoo with a name, 7 pounds 6 ounces and a heart", ["7lb 6oz"]),
    ("Script tattoo with the date 12.3.19 on the arm", ["12.03.19"]),                     # the nought dropped
    ("Script tattoo with the date 12032019 on the arm", ["12.03.2019"]),                  # the parts run together
    ("Script tattoo with the date 12.03.19 on the arm", ["Born 12.03.19"]),               # a label in the item
    ("Script tattoo of the name Della on the wrist", ["Della"]),                          # names that also join names
    ("Script tattoo of the name Van on the wrist", ["Van"]),
    ("Paw print tattoo with the name Oz on the ankle", ["Oz"]),
    ("Script tattoo of the initials J.M. with a heart on the wrist", ["J.M."]),
    ("Script tattoo of the name Olivia down the spine", ["O L I V I A"]),
    ("Script tattoo of the name Maryjane on the hand", ["Mary Jane"]),
    ("Script tattoo of the name नेहा on the wrist", ["नेहा"]),                              # a word with vowel signs
    ("Script tattoo of the names Ava+Noah on the wrist", ["Noah"]),                       # seen only before the tidy-up
    ("Script tattoo of the name Oliv*ia on the wrist", ["Olivia"]),                       # seen only after it
    ("Script tattoo of the name Olivia on the wrist", ["Olivia 12.03.2019"]),      # a name and a date as one item
    ("Script tattoo of the name Olivia on the wrist", ["Baby Olivia, 7lb 6oz"]),
])
def test_a_caption_that_holds_a_private_detail_keeps_the_photo_off(caption, private):
    """A client's name, a child's birth date or a birth weight must not become public text."""
    with pytest.raises(DescribeError) as e:
        parse_response(reply({**TATTOO, "caption": caption, "private_details": private}))
    assert not e.value.retry
    assert caption not in str(e.value) and not any(p in str(e.value) for p in private)    # the reason is public too


@pytest.mark.parametrize("caption,private", [
    ("Baby footprint tattoo with a name, a date and a birth weight", ["Olivia", "12.03.2019", "7lb 6oz"]),
    ("Memorial tattoo reading Dad with dates in script", ["1950 - 2020"]),
    # a label Claude left in an item must not sink an honest caption
    ("Baby footprints tattoo with a name and a date on the forearm", ["Olivia", "Born on 12.03.2019"]),
    ("Baby footprints tattoo with a name, a date and a birth weight", ["Date of birth 12.03.2019", "Weight 7lb 6oz"]),
    ("Memorial tattoo of a sunrise and sunset with dates", ["Sunrise 12.03.1950", "Sunset 04.05.2020"]),
    ("March hare tattoo from Alice in Wonderland on the thigh", ["12th March 2019"]),
    ("Small initials tattoo with a heart and a date", ["A.J."]),
    ("Script tattoo of a name with 7 roses, 6 stars and a heart", ["7lb 6oz"]),
    ("Script name tattoo with a banner and a rose on the forearm", ["Ann"]),       # Ann is inside "banner"
    ("Full sleeve of roses with a name in script", ["Eve"]),                       # Eve is inside "sleeve"
    ("Script tattoo of names and a date on the forearm", ["Ava and Noah", "3/11/21"]),    # "and" is no name
    ("Coordinates tattoo reading 53.7632 N with a date beneath", ["7.6.32"]),      # 7632 is part of a longer number
    ("Script tattoo of a name with 7 small stars on the wrist", ["7"]),            # one figure alone is no detail
    ("Script tattoo of a name with 76 small stars on the wrist", ["7lb 6oz"]),     # 76 is not 7lb 6oz
    ("Script tattoo of a name beside a 1766 coin on the wrist", ["7-6"]),          # 76 inside a longer number
    ("Boxing gloves tattoo marked 16 oz with a name and a birth weight", ["7 lb 6 oz"]),    # "oz" is a unit, no name
    ("St Christopher medal tattoo with a name and a date", ["1st June 2019"]),     # the "st" of 1st is no name
    ("Dia de los Muertos skull tattoo with a name on the calf", ["Ana de la Cruz"]),      # "de" joins a surname
    ("Black and grey snake tattoo on the forearm", []),
])
def test_a_caption_that_keeps_the_private_details_out_is_published_as_written(caption, private):
    d = parse_response(reply({**TATTOO, "caption": caption, "private_details": private}))
    assert d.caption == caption


@pytest.mark.parametrize("payload", [
    {"finished_tattoo": True, "caption": "Black and grey snake tattoo on the forearm", "kinds": ["small"]},
    {**TATTOO, "private_details": None},
    {**TATTOO, "private_details": "Olivia"},
    {**TATTOO, "private_details": ["Olivia", 7]},
    {**TATTOO, "private_details": ["Name%d" % i for i in range(51)]},       # far more than any tattoo holds
    {**TATTOO, "private_details": ["Olivia " * 30]},
    {**TATTOO, "caption": 5},
    {**TATTOO, "kinds": None},
])
def test_an_answer_with_no_proper_private_list_is_not_published(payload):
    """No list, no check: a caption is never published unchecked."""
    with pytest.raises(DescribeError) as e:
        parse_response(reply(payload))
    assert not e.value.retry


def test_the_private_list_goes_no_further_than_the_check():
    """state.json, the run log and the commit message are public. What sync.py gets has no list in it."""
    d = parse_response(reply({**TATTOO, "caption": "Baby footprint tattoo with a name and a date",
                              "private_details": ["Olivia", "12.03.2019"]}))
    assert [f.name for f in dataclasses.fields(d)] == ["finished_tattoo", "caption", "kinds"]
    assert "Olivia" not in repr(d) and "2019" not in repr(d)


def check_with(monkeypatch, tmp_path, answer):
    """Run describe.py --check on one generated photo, with Claude's answer canned."""
    photo = tmp_path / "photo.jpg"
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (150, 90, 60)).save(buffer, "JPEG")
    photo.write_bytes(buffer.getvalue())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(describe, "make_describer", lambda key: lambda jpeg, caption: parse_response(reply(answer)))
    return describe.main(["--check", str(photo)])


def test_the_check_command_prints_the_caption_and_never_the_private_list(monkeypatch, tmp_path, capsys):
    """describe.py --check runs on GitHub, and its log is public."""
    code = check_with(monkeypatch, tmp_path, {**TATTOO, "caption": "Baby footprint tattoo with a name and a date",
                                              "private_details": ["Olivia", "12.03.2019"]})
    out = capsys.readouterr().out
    assert code == 0 and "Baby footprint tattoo with a name and a date" in out
    assert "Olivia" not in out and "2019" not in out


def test_the_check_command_prints_neither_a_caption_that_slipped_nor_the_name_in_it(monkeypatch, tmp_path, capsys):
    code = check_with(monkeypatch, tmp_path, {**TATTOO, "caption": "Script tattoo of the name Olivia on the wrist",
                                              "private_details": ["Olivia"]})
    out = capsys.readouterr().out
    assert code == 1 and "private detail" in out
    assert "Olivia" not in out


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
