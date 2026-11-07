"""Editing the gallery of a page body, and nothing else.

A gallery is the run of photo lines inside the <div class="gallery"> that follows a heading:

    <h2 id="recent-h">Recent work</h2>
    <div class="gallery">
      <!--photo file.jpg | caption -->
      <!--photo file.jpg | caption | classes -->
    </div>

Everything outside those lines is Caitlin's words and is never touched. A gallery that holds
anything but photo lines raises GalleryError rather than being guessed at.
"""
import re

# Same pattern as make.py: <!--photo file.jpg | alt text | extra classes -->
PHOTO_RE = re.compile(r"<!--photo\s+(\S+)\s*\|\s*(.*?)\s*(?:\|\s*(.*?)\s*)?-->")
OPEN = '<div class="gallery">'
CLOSE = "</div>"
DEFAULT_INDENT = "      "


class GalleryError(Exception):
    pass


def photo_line(file, caption, classes=""):
    if classes:
        return f"<!--photo {file} | {caption} | {classes} -->"
    return f"<!--photo {file} | {caption} -->"


def _file_of(line):
    m = PHOTO_RE.search(line)
    return m.group(1) if m else None


def _block(text, heading_id):
    """Start and end of the text inside the gallery div that follows the heading."""
    h = text.find(f'id="{heading_id}"')
    if h < 0:
        raise GalleryError(f'no heading with id="{heading_id}"')
    o = text.find(OPEN, h)
    if o < 0:
        raise GalleryError(f'no gallery after id="{heading_id}"')
    start = o + len(OPEN)
    end = text.find(CLOSE, start)
    if end < 0:
        raise GalleryError("gallery never closes")
    for line in text[start:end].splitlines():
        s = line.strip()
        if s and not (s.startswith("<!--photo") and s.endswith("-->")):
            raise GalleryError(f"unexpected content in the gallery: {s[:60]}")
    return start, end


def gallery_lines(text, heading_id):
    start, end = _block(text, heading_id)
    return [line for line in text[start:end].split("\n") if line.strip()]


def add_photo(text, heading_id, file, caption, keep):
    """Put a new photo line first in the gallery. Beyond `keep` lines the oldest drop off
    (None keeps them all). A file already in the gallery is left where it is."""
    start, end = _block(text, heading_id)
    inner = text[start:end]
    lines = [line for line in inner.split("\n") if line.strip()]
    if any(_file_of(line) == file for line in lines):
        return text
    indent = re.match(r"\s*", lines[0]).group(0) if lines else DEFAULT_INDENT
    lines = [indent + photo_line(file, caption)] + lines
    if keep is not None:
        lines = lines[:keep]
    tail = inner.rsplit("\n", 1)[1] if "\n" in inner else ""
    return text[:start] + "\n" + "\n".join(lines) + "\n" + tail + text[end:]


def set_caption(text, file, caption):
    def repl(m):
        if m.group(1) != file:
            return m.group(0)
        return photo_line(file, caption, m.group(3) or "")
    return PHOTO_RE.sub(repl, text)


def remove_photo(text, file):
    return "\n".join(line for line in text.split("\n") if _file_of(line) != file)


def has_photo(text, file):
    return any(m.group(1) == file for m in PHOTO_RE.finditer(text))
