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
# questions, hype. A bang at the very end of the line is forgiven.
REJECT_CHARS = set("#@£$?!")
# Punctuation that may stay in a caption. Everything else that is not a letter, digit or
# space is dropped (emoji, symbols, |, <, >).
ALLOWED_PUNCT = set(",.'’\"-&()/:;")
# A full stop after one of these is not the end of a sentence.
ABBREVIATIONS = {"st", "mr", "mrs", "ms", "dr", "no", "mt", "fr", "sr", "jr", "rev", "vs"}
TOKEN_BEFORE_DOT = re.compile(r"([A-Za-z]+)\.$")
WORD_EDGES = ",.;:()\"'’"


def load_rules(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _is_abbreviation(text_up_to_dot):
    m = TOKEN_BEFORE_DOT.search(text_up_to_dot)
    return bool(m) and (len(m.group(1)) == 1 or m.group(1).lower() in ABBREVIATIONS)


def _sentences(line):
    parts, start = [], 0
    for m in re.finditer(r"\.\s+", line):
        if _is_abbreviation(line[start:m.start() + 1]):
            continue
        parts.append(line[start:m.end()].strip())
        start = m.end()
    parts.append(line[start:].strip())
    return [p for p in parts if p]


def _candidates(caption):
    """Each line of the caption, then each sentence inside a line, then the whole line."""
    for line in caption.splitlines():
        if not line.strip():
            continue
        parts = _sentences(line)
        yield from parts
        if len(parts) > 1:
            yield line.strip()


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


def tidy(text):
    """Any caption, tidied the way hers are: symbols out, spaces even, first letter a capital."""
    text = _clean(text or "")
    return text[0].upper() + text[1:] if text else ""


def _words(text):
    return [w for w in text.split() if re.search(r"[^\W_]", w)]


def _phrase_matches(text_lower, phrase):
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return list(re.finditer(pattern, text_lower))


def _has_phrase(text_lower, phrases):
    return any(_phrase_matches(text_lower, p) for p in phrases)


def _has_place(text_lower, rules):
    """A place word counts. A short word that is also everyday English (back, side, hand...)
    counts only next to a qualifier: 'the back', 'her hand', 'lower back', 'hand piece'."""
    ambiguous = set(rules.get("ambiguous", []))
    qualifiers = set(rules.get("qualifiers", []))
    for phrase in sorted(rules["places"], key=len, reverse=True):
        for m in _phrase_matches(text_lower, phrase):
            if phrase not in ambiguous:
                return True
            before = text_lower[:m.start()].split()
            after = text_lower[m.end():].split()
            prev = before[-1].strip(WORD_EDGES) if before else ""
            nxt = after[0].strip(WORD_EDGES) if after else ""
            if prev in qualifiers or nxt in ("piece", "tattoo"):
                return True
    return False


def site_caption(caption, rules):
    if not caption:
        return None
    banned = set(rules["banned"])
    for raw in _candidates(caption):
        raw = re.sub(r"[!.\s]+$", "", raw.strip())
        low = raw.lower()
        if any(c in raw for c in REJECT_CHARS) or "http" in low or "www." in low:
            continue
        text = _clean(raw)
        words = _words(text)
        if not rules["min_words"] <= len(words) <= rules["max_words"]:
            continue
        if any(w.lower().strip(WORD_EDGES) in banned for w in words):
            continue
        if _has_phrase(text.lower(), rules.get("reject_phrases", [])):
            continue
        if not _has_place(text.lower(), rules):
            continue
        return text[0].upper() + text[1:]
    return None


def pages_for(caption, rules):
    low = caption.lower()
    return [page for page, words in rules["pages"].items() if _has_phrase(low, words)]
