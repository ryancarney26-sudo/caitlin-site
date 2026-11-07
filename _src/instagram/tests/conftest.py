"""Shared test fixtures for the Instagram robot.

repo_copy: a throwaway copy of the site sources (_src without the robot's own folder) plus
empty placeholder files for every image the pages reference, so make.py can build and the
gallery editors can be exercised without touching the real checkout.
"""
import pathlib
import re
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
INSTAGRAM = HERE.parent          # _src/instagram
SRC = INSTAGRAM.parent           # _src

for p in (INSTAGRAM, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

IMAGE_REF = re.compile(r"<!--(?:photo|arch)\s+(\S+)")
META_IMAGE = re.compile(r"^(?:hero|og):\s*([^|\n]+)", re.M)


def referenced_image_names(pages_dir: pathlib.Path) -> set[str]:
    names = {"share-home.jpg"}
    for page in pages_dir.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        names.update(IMAGE_REF.findall(text))
        names.update(m.strip() for m in META_IMAGE.findall(text))
    return names


@pytest.fixture
def repo_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "site"
    shutil.copytree(SRC, root / "_src", ignore=shutil.ignore_patterns("instagram", "__pycache__"))
    images = root / "images"
    images.mkdir()
    for name in referenced_image_names(root / "_src" / "pages"):
        (images / name).write_bytes(b"")
    return root
