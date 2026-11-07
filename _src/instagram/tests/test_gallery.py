"""Editing the photo lines of a page's gallery, and touching nothing else."""
import pytest

from gallery import (GalleryError, add_photo, gallery_lines, has_photo, photo_line,
                     remove_photo, set_caption)

NEW = "tattoo-preston-twisty-snake-20261107.jpg"

SNIPPET = """<section aria-labelledby="photos-h">
    <h2 id="photos-h">Portraits I've done</h2>
    <div class="gallery">
      <!--photo a.jpg | Old caption | feature -->
      <!--photo b.jpg | Second -->
    </div>
  </section>
  <section aria-labelledby="other-h">
    <h2 id="other-h">Other</h2>
    <div class="gallery">
      <!--photo a.jpg | Old caption -->
    </div>
  </section>"""


def home(repo_copy):
    return (repo_copy / "_src" / "pages" / "00-home.html").read_text(encoding="utf-8")


def around(text, heading_id="recent-h"):
    """The text before the gallery's lines and the text after them."""
    i = text.index('<div class="gallery">', text.index(f'id="{heading_id}"')) + len('<div class="gallery">')
    j = text.index("</div>", i)
    return text[:i], text[j:]


# The live home gallery grows as the robot adds photos, so these count from the page as it is.

def test_gallery_lines_home(repo_copy):
    lines = gallery_lines(home(repo_copy), "recent-h")
    assert len(lines) >= 8
    assert all(line.strip().startswith("<!--photo") for line in lines)
    assert any("tattoo-preston-medusa.jpg | Medusa" in line for line in lines)


def test_add_photo_goes_first_and_trims(repo_copy):
    before = gallery_lines(home(repo_copy), "recent-h")
    out = add_photo(home(repo_copy), "recent-h", NEW, "Twisty snake, forearm", keep=len(before))
    lines = gallery_lines(out, "recent-h")
    assert lines[0].strip() == f"<!--photo {NEW} | Twisty snake, forearm -->"
    assert lines[0].startswith("      <!--photo")
    assert len(lines) == len(before)
    assert before[-1] not in lines                     # the oldest dropped off
    assert lines[1] == before[0]                       # the old first tile, untouched, now second
    assert any("| feature" in line for line in lines)  # the feature tile keeps its class


def test_add_keeps_everything_outside_gallery(repo_copy):
    before = home(repo_copy)
    after = add_photo(before, "recent-h", NEW, "Twisty snake, forearm", keep=8)
    assert around(before) == around(after)


def test_add_to_subject_page_never_trims(repo_copy):
    text = (repo_copy / "_src" / "pages" / "10-portrait-tattoos.html").read_text(encoding="utf-8")
    assert len(gallery_lines(text, "photos-h")) == 7
    out = add_photo(text, "photos-h", NEW, "Portrait, forearm", keep=None)
    assert len(gallery_lines(out, "photos-h")) == 8


def test_add_is_idempotent(repo_copy):
    once = add_photo(home(repo_copy), "recent-h", NEW, "Twisty snake, forearm", keep=12)
    twice = add_photo(once, "recent-h", NEW, "Twisty snake, forearm", keep=12)
    assert twice == once
    assert sum(NEW in line for line in gallery_lines(twice, "recent-h")) == 1


def test_set_caption_preserves_classes():
    out = set_caption(SNIPPET, "a.jpg", "New")
    assert "<!--photo a.jpg | New | feature -->" in out
    assert "<!--photo a.jpg | New -->" in out
    assert "Old caption" not in out
    assert "<!--photo b.jpg | Second -->" in out


def test_remove_photo_from_every_gallery():
    out = remove_photo(SNIPPET, "a.jpg")
    assert "a.jpg" not in out
    assert "<!--photo b.jpg | Second -->" in out
    assert not has_photo(out, "a.jpg") and has_photo(out, "b.jpg")


def test_gallery_error_on_unexpected_content():
    bad = SNIPPET.replace('<!--photo b.jpg | Second -->', '<img src="/images/b.jpg">')
    with pytest.raises(GalleryError):
        gallery_lines(bad, "photos-h")


def test_missing_heading_raises():
    with pytest.raises(GalleryError):
        gallery_lines(SNIPPET, "nope-h")


def test_photo_line():
    assert photo_line("a.jpg", "Cap") == "<!--photo a.jpg | Cap -->"
    assert photo_line("a.jpg", "Cap", "feature") == "<!--photo a.jpg | Cap | feature -->"
