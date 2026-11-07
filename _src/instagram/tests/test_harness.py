"""The test harness itself: a throwaway copy of the site to build and edit in."""


def test_repo_copy_has_pages_and_images(repo_copy):
    assert (repo_copy / "_src" / "pages" / "00-home.html").exists()
    assert (repo_copy / "_src" / "template.html").exists()
    assert (repo_copy / "images" / "tattoo-preston-medusa.jpg").exists()
    assert (repo_copy / "images" / "share-home.jpg").exists()
    # The robot's own folder is not part of the copy: tests write there, never into the real one.
    assert not (repo_copy / "_src" / "instagram").exists()
