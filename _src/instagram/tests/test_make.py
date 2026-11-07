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


def test_all_my_tattoos_page_is_built_and_linked(repo_copy):
    r = build(repo_copy, "--final")
    assert r.returncode == 0, r.stdout + r.stderr
    archive = (repo_copy / "tattoos" / "index.html").read_text(encoding="utf-8")
    assert "<h1>All my tattoos</h1>" in archive
    assert 'href="/tattoos/"' in (repo_copy / "portrait-tattoos" / "index.html").read_text(encoding="utf-8")
    assert 'href="/tattoos/"' in (repo_copy / "index.html").read_text(encoding="utf-8")
    assert "https://caitlincarneytattoo.co.uk/tattoos/" in (repo_copy / "sitemap.xml").read_text(encoding="utf-8")


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
