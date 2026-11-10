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
import re
import sys
import unicodedata
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
        # Before the caption, so the details are in front of Claude when it writes the line that must not hold them
        "private_details": {"type": "array", "items": {"type": "string"}},
        "caption": {"type": "string"},
        "kinds": {"type": "array", "items": {"type": "string", "enum": list(KINDS)}},
    },
    "required": ["finished_tattoo", "private_details", "caption", "kinds"],
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
personal, such as a quote or an ordinary word like Love or Blessed, may be given as they read.

Put each such name, date and birth weight in private_details instead, exactly as it is written in \
the tattoo, one to an item and with no other word around it: "Olivia", not "Baby Olivia"; \
"12.03.2019", not "Born 12.03.2019"; "7lb 6oz", not "Weight 7lb 6oz". A year on its own, a time of \
birth and a person's initials count as well. If a name is not in English letters, or a date is in \
Roman numerals, list it twice: as written, and in English letters or in figures.

Whatever you list must stay out of the caption: a caption that holds a listed item is thrown \
away. So list only what you have left out. Mum, Dad and Nan are not names: write them, and do not \
list them. Nor is the name of a saint, a famous person, a character, a team, a band or a place. \
That list is never published. Leave it empty when the tattoo holds none, and put nothing else in \
it: no quote, no scripture reference, no ordinary word.

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

If it is not a finished tattoo, set finished_tattoo to false, private_details to an empty list, \
caption to an empty string and kinds to an empty list."""


# The check under the privacy rule above: ask, don't guess. Claude lists the private details it can
# read in the tattoo, and a caption that holds any of them keeps the photo off. Nothing is reworded,
# so nothing can be garbled, and no word is taken for a name because of its shape. The list is used
# in parse_response and dropped there: it is never stored, printed or put in an error message,
# because state.json, the run log and the commit message are all public.
MAX_DETAILS, MAX_DETAIL_LENGTH = 50, 100       # far more than any tattoo holds: a longer list is a broken answer
_NEVER_NAMES = {"and", "the", "of"}
# These join the parts of a surname ("Ana de la Cruz"). Alone they are names: Della, Di, Van.
_JOINERS = {"van", "von", "der", "den", "de", "del", "della", "di", "da", "du", "la", "le", "el", "bin", "ap"}
# Words that sit beside a date or a weight, in a tattoo and in an honest caption alike. In an item
# that holds a figure they are labels, not names: "Born on 12.03.2019", "Sunrise 12.03.1950".
_LABELS = {"name", "names", "date", "dates", "dob", "born", "birth", "died", "death", "weight", "time", "length",
           "sunrise", "sunset", "est", "since", "on", "in", "at", "to", "from", "until", "age", "aged",
           "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
           "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"}
_UNITS = {"lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb", "oz": "oz", "ozs": "oz", "ounce": "oz",
          "ounces": "oz", "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg"}
_AFTER_A_FIGURE = set(_UNITS.values()) | {"st", "nd", "rd", "th", "am", "pm", "cm", "mm", "g"}     # 1st, 10am, 52cm


def _plain(text):
    """Lower case with the accents off, so that ZOË, Zoë and Zoe are one name."""
    stripped = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return stripped.casefold()


def _runs(text):
    """The text as runs of letters and runs of figures, in order: "7lb 6oz" -> 7, lb, 6, oz.
    A mark that belongs to a letter stays in its word, so a name in Hindi is one run."""
    runs, kind = [], None
    for ch in _plain(text):
        category = unicodedata.category(ch)
        now = "word" if category[0] in "LM" else "figure" if category == "Nd" else None
        if now and now == kind:
            runs[-1] += ch
        elif now:
            runs.append(ch)
        kind = now
    return runs


def _same_form(runs):
    """Figures without leading noughts (03 is 3), and a unit after a figure in one spelling (lbs is lb)."""
    out = []
    for i, run in enumerate(runs):
        if run.isdigit():
            out.append(run.lstrip("0") or "0")
        elif i and runs[i - 1].isdigit():
            out.append(_UNITS.get(run, run))
        else:
            out.append(run)
    return out


def _side_by_side(part, whole):
    return any(whole[i:i + len(part)] == part for i in range(len(whole) - len(part) + 1))


def holds_private_detail(caption, details):
    """True when the caption holds one of the names, dates or weights Claude read in the tattoo.

    Caption and item are split into runs of letters and runs of figures, so the marks and spaces
    between them never matter and a figure next door cannot hide a match.
    - A name counts when one of its words is a whole word of the caption: Ann is not in "banner".
    - A date or a weight counts when its runs stand side by side in the caption, when its figures
      appear as one number (12032019), or when its year appears (12.03.2019 in "12 March 2019").
    - Initials count side by side (J.M.), and spaced letters count as the word they spell."""
    written = _runs(caption)
    runs = _same_form(written)
    words = {run for run in runs if not run.isdigit()}
    numbers = {run for run in runs if run.isdigit()}
    for detail in details:
        item_written = _runs(detail)
        item = _same_form(item_written)
        figures = [i for i, run in enumerate(item) if run.isdigit()]
        names = [run for i, run in enumerate(item)
                 if not run.isdigit() and len(run) > 1 and run not in _NEVER_NAMES
                 and not (figures and run in _LABELS)
                 and not (i and item[i - 1].isdigit() and run in _AFTER_A_FIGURE)]
        if any(name in words for name in ([n for n in names if n not in _JOINERS] or names)):
            return True
        if figures:
            end = figures[-1] + 1
            if end < len(item) and item[end] in _AFTER_A_FIGURE:
                end += 1
            core = item[figures[0]:end]                       # the item without the labels around it
            if (len(core) > 1 or len(core[0]) > 1) and _side_by_side(core, runs):
                return True
            glued = "".join(item_written[i] for i in figures)
            if len(figures) > 1 and len(glued) >= 6 and glued in written:      # a date run together, not 7lb 6oz as 76
                return True
            if any(len(item[i]) == 4 and item[i][0] in "12" and item[i] in numbers for i in figures):
                return True
        elif len(item) > 1 and (_side_by_side(item, runs) or "".join(item) in words):
            return True
    return False


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
    private = data.get("private_details")
    kinds = data.get("kinds", [])
    if (not isinstance(raw, str) or not isinstance(kinds, list) or not isinstance(private, list)
            or len(private) > MAX_DETAILS
            or not all(isinstance(detail, str) and len(detail) <= MAX_DETAIL_LENGTH for detail in private)):
        raise DescribeError("Claude's answer could not be read", retry=False)      # no list, no check: never publish unchecked
    if "#" in raw or "@" in raw:
        raise DescribeError("Claude's caption broke the rules: it held a hashtag or an @name", retry=False)
    caption = tidy(raw)
    if holds_private_detail(raw, private) or holds_private_detail(caption, private):
        raise DescribeError("Claude's caption held a private detail from the tattoo", retry=False)
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
