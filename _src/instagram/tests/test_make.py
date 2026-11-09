"""make.py builds into the repository root, and --final refuses to build with a missing image.
It also keeps every route to a booking pointed at Caitlin: the studio's form does not list her."""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

SITE_CSS = pathlib.Path(__file__).resolve().parents[3] / "assets" / "site.css"
STUDIO_FORM = "https://www.truecolourstattoo.co.uk/quotation-booking-request"
PROFILE = "https://www.instagram.com/caitlincarneytattoo/"
CHAT = "https://ig.me/m/caitlincarneytattoo"
# A row of buttons, and the tip paragraph straight after it when there is one
ACTIONS = re.compile(r'<div class="actions">(.*?)</div>(\s*<p class="form-tip">.*?</p>)?', re.S)
FLOAT = re.compile(r'id="book-float" href="([^"]*)"')
IG_CHAT_SCRIPT = re.compile(r'<script id="ig-chat">(.*?)</script>', re.S)


def build(repo, *args):
    return subprocess.run(
        [sys.executable, "-I", str(repo / "_src" / "make.py"), *args],
        capture_output=True, text=True, cwd=repo,
    )


def built(repo, page="index.html"):
    r = build(repo, "--final")
    assert r.returncode == 0, r.stdout + r.stderr
    return (repo / page).read_text(encoding="utf-8")


def built_pages(repo):
    return sorted(p for p in repo.rglob("index.html") if "_src" not in p.parts)


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


def test_every_studio_form_button_carries_the_for_caitlin_tip(repo_copy):
    """The studio's form has no place to choose Caitlin, so each button that leads to it must say
    how to make the enquiry reach her. A page added later gets the tip without anyone remembering."""
    built(repo_copy)
    checked = 0
    for page in built_pages(repo_copy):
        for m in ACTIONS.finditer(page.read_text(encoding="utf-8")):
            if STUDIO_FORM in m.group(1):
                checked += 1
                assert m.group(2) and "For Caitlin Carney" in m.group(2), f"{page}: a studio-form button has no tip"
    assert checked, "no studio-form buttons were found, so this test checked nothing"


def test_buttons_that_do_not_lead_to_the_studio_form_get_no_tip(repo_copy):
    # The walk-in page's buttons ring the studio and open the prices: the tip would make no sense there
    assert "form-tip" not in built(repo_copy, "walk-in-tattoos/index.html")


def test_no_link_to_the_studio_form_sits_outside_a_row_that_has_the_tip(repo_copy):
    """A link to the form written into a sentence, or in a row the build did not recognise, would
    send people there with no word about Caitlin. Count every visible link, not only the rows."""
    built(repo_copy)
    link = f'href="{STUDIO_FORM}"'
    for page in built_pages(repo_copy):
        html = page.read_text(encoding="utf-8")
        with_tip = sum(m.group(1).count(link) for m in ACTIONS.finditer(html) if m.group(2))
        assert html.count(link) == with_tip, f"{page}: a link to the studio's form has no tip beside it"


def test_only_the_row_with_the_form_link_gets_the_tip(repo_copy):
    page = repo_copy / "_src" / "pages" / "30-lancashire.html"
    page.write_text(page.read_text(encoding="utf-8") + """
  <section aria-labelledby="two-h">
    <h2 id="two-h">Two rows</h2>
    <div class="actions">
      <a class="btn" href="/prices/">Prices</a>
    </div>
    <div class="actions">
      <a class="btn primary" href="%s">Send a booking request</a>
    </div>
  </section>
""" % STUDIO_FORM, encoding="utf-8", newline="\n")
    rows = [(STUDIO_FORM in m.group(1), bool(m.group(2)))
            for m in ACTIONS.finditer(built(repo_copy, "lancashire/index.html"))]
    assert rows == [(False, False), (True, True)]      # (leads to the form, has the tip) for each row


@pytest.mark.parametrize("page,href", [
    ("portrait-tattoos/index.html", "/prices/#book"),   # her own booking steps, where the tip is
    ("about/index.html", "/prices/#book"),
    ("prices/index.html", "#book"),                      # already on that page
    ("index.html", "#book"),
    ("walk-in-tattoos/index.html", "tel:+441772378565"),
])
def test_floating_button_never_goes_straight_to_the_studio_form(repo_copy, page, href):
    """On a phone the floating button is the one in reach, and there is no room beside it for the
    tip. So it leads to her booking steps, never straight to a form that does not list her."""
    assert FLOAT.search(built(repo_copy, page)).group(1) == href


def test_the_booking_steps_the_floating_button_leads_to_exist(repo_copy):
    assert 'id="book"' in built(repo_copy, "prices/index.html")
    assert 'id="book"' in (repo_copy / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("page", ["prices/index.html", "index.html"])
def test_the_booking_section_keeps_still_so_a_jump_lands_where_it_aimed(repo_copy, page):
    """Sections rise into view. A section that rises after the browser has jumped to it ends up
    above where the jump landed, with its heading under the header. So the section a link jumps to
    keeps still, and what is inside it rises instead."""
    tag, first_child = re.search(r'(<section\b[^>]*\bid="book"[^>]*>)\s*(<[^>]+>)', built(repo_copy, page)).groups()
    assert "reveal" not in tag
    assert first_child == '<div class="reveal">'


def test_a_jump_to_the_booking_steps_lands_clear_of_the_sticky_header():
    """The header stays stuck to the top of the screen and is up to 118px tall on a narrow phone.
    With no room kept above the booking steps, "How to book" lands with their heading hidden under
    it. The room was measured in a phone-sized browser; this only guards that it is not taken away."""
    css = SITE_CSS.read_text(encoding="utf-8")
    room = [float(rem) for rem in re.findall(r"#book\s*\{\s*scroll-margin-top:\s*([\d.]+)rem", css)]
    assert room, "site.css keeps no room above the booking steps"
    assert max(room) >= 7.5                 # 118px of header, in rem


def test_two_buttons_with_one_name_never_lead_to_two_places(repo_copy):
    """The floating button once shared the name "Get a quote" with a button that opens the studio's
    form, while leading somewhere else. Same name, different result: confusing, most of all to
    someone using a screen reader."""
    built(repo_copy)
    for page in built_pages(repo_copy):
        html = page.read_text(encoding="utf-8")
        href, label = re.search(r'id="book-float" href="([^"]*)">([^<]*)</a>', html).groups()
        same_name = set(re.findall(r'<a [^>]*href="([^"]*)"[^>]*>' + re.escape(label) + r'</a>', html))
        assert same_name == {href}, f"{page}: '{label}' leads to {sorted(same_name)}"


def run_ig_chat_script(script, fine_pointer):
    """Run the page's own inline script in Node against a stand-in page with two marked links.
    Gives back the links' addresses afterwards, and the media queries the script asked about."""
    program = """
const code = %s;
const anchors = [{ href: %s }, { href: %s }];
const asked = [];
const window = { matchMedia: (q) => { asked.push(q); return { matches: %s }; } };
const document = { querySelectorAll: (sel) => (sel === 'a[data-ig-chat]' ? anchors : []) };
new Function('window', 'document', code)(window, document);
console.log(JSON.stringify({ hrefs: anchors.map((a) => a.href), asked }));
""" % (json.dumps(script), json.dumps(PROFILE), json.dumps(PROFILE), "true" if fine_pointer else "false")
    r = subprocess.run([shutil.which("node"), "-"], input=program, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    return out["hrefs"], out["asked"]


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the page's script")
def test_message_me_on_instagram_opens_the_chat_on_a_phone_and_her_profile_on_a_computer(repo_copy):
    """ig.me links open the chat in the app, but do not work on Instagram's website. So the link is
    her profile in the page itself, and the page's script swaps it only on touch devices."""
    home = built(repo_copy)
    marked = re.findall(r'<a [^>]*data-ig-chat[^>]*>', home)
    assert marked, "the home page has no link marked data-ig-chat"
    assert all(f'href="{PROFILE}"' in a for a in marked)       # no script, or a computer: her profile
    script = IG_CHAT_SCRIPT.search(home).group(1)
    a_mouse_and_hover = ["(hover: hover) and (pointer: fine)"]  # the same test site.js uses for "a computer"
    assert run_ig_chat_script(script, fine_pointer=False) == ([CHAT, CHAT], a_mouse_and_hover)
    assert run_ig_chat_script(script, fine_pointer=True) == ([PROFILE, PROFILE], a_mouse_and_hover)


def test_every_message_me_on_instagram_button_is_marked_for_the_chat(repo_copy):
    built(repo_copy)
    found = 0
    for page in built_pages(repo_copy):
        for a in re.findall(r'<a [^>]*>Message me on Instagram</a>', page.read_text(encoding="utf-8")):
            found += 1
            assert "data-ig-chat" in a, f"{page}: a Message me on Instagram button would open her profile on a phone"
    assert found, "no Message me on Instagram buttons were found, so this test checked nothing"
