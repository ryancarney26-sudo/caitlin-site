"""make.py builds into the repository root, and --final refuses to build with a missing image."""
import subprocess
import sys


def build(repo, *args):
    return subprocess.run(
        [sys.executable, "-I", str(repo / "_src" / "make.py"), *args],
        capture_output=True, text=True, cwd=repo,
    )


def test_final_build_writes_pages(repo_copy):
    r = build(repo_copy, "--final")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (repo_copy / "index.html").exists()
    assert (repo_copy / "portrait-tattoos" / "index.html").exists()
    assert (repo_copy / "sitemap.xml").exists()


def test_final_build_refuses_missing_image(repo_copy):
    (repo_copy / "images" / "tattoo-preston-medusa.jpg").unlink()
    r = build(repo_copy, "--final")
    assert r.returncode != 0
    assert "tattoo-preston-medusa.jpg" in r.stdout + r.stderr
    assert not (repo_copy / "index.html").exists()


def test_draft_build_tolerates_missing_image(repo_copy):
    (repo_copy / "images" / "tattoo-preston-medusa.jpg").unlink()
    r = build(repo_copy)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (repo_copy / "index.html").exists()
