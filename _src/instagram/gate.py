"""The caption gate.

An Instagram caption goes on the site only through one plain line that says what the tattoo
is and where on the body it sits. The line is Caitlin's own words; this module only finds it
and tidies it. No line, no photo.

    site_caption(caption, rules) -> the line for the site, or None
    pages_for(caption, rules)    -> the subject pages the line belongs on, by word
"""
import json
import pathlib
import re
import unicodedata

# Any of these in a candidate means it is not a plain description: hashtags, @names, prices,
# questions, hype.
REJECT_CHARS = set("#@£$?!")
# Punctuation that may stay in a caption. Everything else that is not a letter, digit or
# space is dropped (emoji, symbols, |, <, >).
ALLOWED_PUNCT = set(",.'’\"-&()/:;")
SENTENCE_SPLIT = re.compile(r"(?<=\.)\s+")


def load_rules(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _candidates(caption):
    """Each line of the caption, then each sentence inside a line, in order."""
    for line in caption.splitlines():
        for part in SENTENCE_SPLIT.split(line):
            if part.strip():
                yield part


def _clean(raw):
    kept = []
    for ch in unicodedata.normalize("NFC", raw):
        cat = unicodedata.category(ch)
        if cat[0] in "LN" or ch in ALLOWED_PUNCT:
            kept.append(ch)
        elif cat[0] == "Z":
            kept.append(" ")
    text = re.sub(r"\s+", " ", "".join(kept)).strip()
    text = re.sub(r"-{2,}", "-", text)
    return text.strip(" .,;:-")


def _words(text):
    return [w for w in text.split() if re.search(r"[^\W_]", w)]


def _has_phrase(text_lower, phrases):
    for phrase in sorted(phrases, key=len, reverse=True):
        pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, text_lower):
            return True
    return False


def site_caption(caption, rules):
    if not caption:
        return None
    banned = set(rules["banned"])
    for raw in _candidates(caption):
        low = raw.lower()
        if any(c in raw for c in REJECT_CHARS) or "http" in low or "www." in low:
            continue
        text = _clean(raw)
        words = _words(text)
        if not rules["min_words"] <= len(words) <= rules["max_words"]:
            continue
        if any(w.lower().strip(",.;:()\"'’") in banned for w in words):
            continue
        if not _has_phrase(text.lower(), rules["places"]):
            continue
        return text[0].upper() + text[1:]
    return None


def pages_for(caption, rules):
    low = caption.lower()
    return [page for page, words in rules["pages"].items() if _has_phrase(low, words)]
