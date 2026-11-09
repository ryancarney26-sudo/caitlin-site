"""Claude looks at one photo from Caitlin's Instagram and says two things: is this a finished
tattoo, and what one plain line describes it (what it shows, its style, where it sits).

    make_describer(api_key)          -> a function (jpeg bytes, her Instagram caption) -> Description
    python -I _src/instagram/describe.py --check FILE [FILE ...]
                                     prints what Claude says about each photo. Costs about 2p a photo.

Her own line, when she writes one, always wins over Claude's; that choice is made in sync.py.
"""
import argparse
import base64
import json
import os
import pathlib
import sys
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from gate import tidy                      # noqa: E402

MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"   # a declined photo is re-run on another model
MAX_TOKENS = 4000
MIN_WORDS, MAX_WORDS = 3, 20

# Each kind sends the photo to one subject page as well as the home page.
KINDS = {
    "portrait": "10-portrait-tattoos.html",
    "script": "12-script-tattoos.html",
    "christian": "13-christian-tattoos.html",
    "small": "15-walk-in-tattoos.html",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "finished_tattoo": {"type": "boolean"},
        "caption": {"type": "string"},
        "kinds": {"type": "array", "items": {"type": "string", "enum": list(KINDS)}},
    },
    "required": ["finished_tattoo", "caption", "kinds"],
    "additionalProperties": False,
}

SYSTEM = """You write captions for the gallery on caitlincarneytattoo.co.uk, the portfolio site of \
Caitlin Carney, a tattoo artist in Preston. Each caption is also the photo's alt text, read by \
visitors, search engines and screen readers.

You get one photo from her Instagram, and her Instagram caption for context.

First decide whether the photo shows a finished tattoo on skin: fresh or healed, or clearly in \
progress. Flash sheets, drawings, paintings, stencils on paper, selfies, event photos, the studio, \
price lists, promotions and text graphics are not finished tattoos.

If it is a finished tattoo, write one plain line of 4 to 16 words in British English. Say what the \
tattoo shows, its style (black and grey, colour, fine line, linework, script) and where on the body \
it sits, when the photo shows that clearly. Leave the body part out rather than guess it. No praise, \
no opinions, no claims about the client or what the tattoo means, no hashtags, no @names, no emoji, \
no full stop.

A name, a date or a birth weight written in a tattoo belongs to the person wearing it. Never copy \
it into the caption: say "a name", "a date" or "a birth weight" instead. Words that are not \
personal, such as a quote or a single word, may be given as they read.

Add no religious wording of your own: no verse text, no blessing, no devotional phrase. A scripture \
reference that can be read clearly in the tattoo, such as Philippians 4:13, may be named.

Match the site's existing captions:
- Medusa tattoo with snakes and a crescent moon, black and grey, upper arm
- Colour tattoo of a robin and a monarch butterfly on a branch
- Portrait tattoo of a father and his baby, black and grey, on the forearm
- Small black and grey butterfly tattoo on the arm
- Crowned crow tattoo on the back of the neck
- Script name tattoo with a crown and a date, black and grey, on the inner forearm

Kinds, any that apply: portrait (a realistic face of a person, pet or character), christian \
(crosses, Jesus, Mary, angels, saints, scripture, rosaries, praying hands), script (lettering is the \
main subject), small (a small piece, or a design from her flash; her caption may say "flash").

If it is not a finished tattoo, set finished_tattoo to false, caption to an empty string and kinds \
to an empty list."""


@dataclass
class Description:
    finished_tattoo: bool
    caption: str
    kinds: list = field(default_factory=list)


class DescribeError(Exception):
    """retry: the same photo may work next hour. stop_all: don't ask Claude again this run."""

    def __init__(self, message, retry, stop_all=False):
        super().__init__(message)
        self.retry = retry
        self.stop_all = stop_all


def error_for_status(status, message):
    if status is None or status == 429 or status >= 500:
        return DescribeError(f"Claude could not be reached ({message})", retry=True)
    # 400, 401, 403, 404...: the key or this code is wrong, not the photo. Never mark a post for good.
    return DescribeError(f"Claude refused the request, HTTP {status} ({message})", retry=True, stop_all=True)


def build_request(jpeg_bytes, instagram_caption):
    if instagram_caption and instagram_caption.strip():
        context = ("Her Instagram caption, for context only; don't copy its chat:\n"
                   + instagram_caption.strip())
    else:
        context = "Her Instagram post has no caption."
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
        "system": SYSTEM,
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(jpeg_bytes).decode("ascii")}},
            {"type": "text", "text": context},
        ]}],
    }


def parse_response(response):
    if response.stop_reason == "refusal":
        raise DescribeError("Claude declined to describe this photo", retry=False)
    if response.stop_reason == "max_tokens":
        raise DescribeError("Claude's answer was cut off", retry=False)
    text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), None)
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        raise DescribeError("Claude's answer could not be read", retry=False) from None
    if not data.get("finished_tattoo"):
        return Description(False, "", [])
    # The reasons below never quote the caption: they are stored in state.json and printed in the
    # run log, the repository is public, and a rejected caption may be the one that holds a name.
    raw = data.get("caption") or ""
    if "#" in raw or "@" in raw:
        raise DescribeError("Claude's caption broke the rules: it held a hashtag or an @name", retry=False)
    caption = tidy(raw)
    words = [w for w in caption.split() if any(ch.isalnum() for ch in w)]
    if not MIN_WORDS <= len(words) <= MAX_WORDS:
        raise DescribeError(f"Claude's caption was the wrong length: {len(words)} words", retry=False)
    return Description(True, caption, [k for k in data.get("kinds", []) if k in KINDS])


def pages_for_kinds(kinds):
    return sorted({KINDS[k] for k in kinds if k in KINDS})


def describe(client, jpeg_bytes, instagram_caption):
    return parse_response(client.beta.messages.create(**build_request(jpeg_bytes, instagram_caption)))


def make_describer(api_key):
    import anthropic                       # only the runs that use Claude need the package

    client = anthropic.Anthropic(api_key=api_key, timeout=120.0, max_retries=2)

    def run(jpeg_bytes, instagram_caption):
        try:
            return describe(client, jpeg_bytes, instagram_caption)
        except anthropic.APIStatusError as e:
            raise error_for_status(e.status_code, e.message) from None
        except anthropic.APIConnectionError as e:          # timeouts included
            raise error_for_status(None, str(e)) from None
    return run


def main(argv=None):
    from images import process_image

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", nargs="+", metavar="FILE", required=True,
                    help="photos to describe; nothing on the site changes")
    args = ap.parse_args(argv)
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("No ANTHROPIC_API_KEY is set, so Claude cannot be asked.")
        return 2
    run = make_describer(key)
    failed = 0
    for path in args.check:
        try:
            d = run(process_image(pathlib.Path(path).read_bytes()), None)
            print(f"{path}: finished tattoo: {d.finished_tattoo}; caption: {d.caption!r}; kinds: {d.kinds}")
        except DescribeError as e:
            failed += 1
            print(f"{path}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
