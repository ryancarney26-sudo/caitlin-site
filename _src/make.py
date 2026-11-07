"""Stamp the shared head, header and footer onto each page body in pages/,
and write the finished HTML into the site folder.

    python make.py            builds the draft: yellow slots and a draft banner stay in
    python make.py --final    refuses to build while any [slot] is left, otherwise strips the banner

Each file in pages/ starts with a meta block:

    <!--meta
    path: /portrait-tattoos/
    title: Portrait tattoos in Preston | Caitlin Carney Tattoo
    description: ...
    service: Portrait tattoos            (optional: adds a Service node to the structured data)
    og: share-portraits.jpg              (optional: the card shown when the page is shared;
                                          share-home.jpg otherwise. Both come from share-card.html)
    -->

Photos are written as one-line comments, so a page builds before the photos exist:

    <!--photo portrait-tattoo-preston-01.jpg | alt text here -->

If images/<file> exists in the site folder it becomes an <img>; otherwise a yellow placeholder.
A --final build refuses to write anything while any referenced image is missing.
"""
import datetime
import json
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parent
OUT = SRC.parent
SITE = "https://caitlincarneytattoo.co.uk"
FINAL = "--final" in sys.argv
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")

STUDIO_ID = "https://www.truecolourstattoo.co.uk/#studio"
PERSON_ID = SITE + "/#caitlin"
WEBSITE_ID = SITE + "/#website"

STUDIO = {
    "@type": "TattooParlor",
    "@id": STUDIO_ID,
    "name": "True Colours Tattoo & Piercing Studio",
    "url": "https://www.truecolourstattoo.co.uk/",
    "telephone": "+441772378565",
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "14 Guildhall Street",
        "addressLocality": "Preston",
        "addressRegion": "Lancashire",
        "postalCode": "PR1 3NU",
        "addressCountry": "GB",
    },
}

PERSON = {
    "@type": "Person",
    "@id": PERSON_ID,
    "name": "Caitlin Carney",
    "alternateName": ["Caitlin Carney Tattoo", "Caitlin O'Brien"],
    "jobTitle": "Tattoo artist",
    "description": "Tattoo artist at True Colours in Preston, Lancashire. Portraits of people, pets and film and TV characters, Christian pieces, script and lettering, and memorial work, in black and grey or colour. Walk-ins Tuesday to Thursday.",
    "url": SITE + "/",
    "worksFor": {"@id": STUDIO_ID},
    "workLocation": {"@id": STUDIO_ID},
    "knowsAbout": [
        "Portrait tattoos",
        "Film and TV character portrait tattoos",
        "Pet portrait tattoos",
        "Christian tattoos",
        "Script and lettering tattoos",
        "Handwriting tattoos",
        "Memorial tattoos",
        "Black and grey tattoos",
        "Colour tattoos",
        "Walk-in tattoos",
    ],
    "sameAs": ["https://www.instagram.com/caitlincarneytattoo/"],
}

WEBSITE = {
    "@type": "WebSite",
    "@id": WEBSITE_ID,
    "url": SITE + "/",
    "name": "Caitlin Carney Tattoo",
    "about": {"@id": PERSON_ID},
}

AREA = [
    {"@type": "City", "name": "Preston"},
    {"@type": "AdministrativeArea", "name": "Lancashire"},
    {"@type": "AdministrativeArea", "name": "North West England"},
]

# The four kinds of work, in the order they appear in the strip at the foot of each page, then the
# page with every photo (added 7 Nov 2026, for the Instagram backfill).
# Cover-ups and memorial came out on 4 Nov 2026: Caitlin does both now and then, but doesn't
# want a page for either until she has enough work to fill it. The drafts are kept in pages-off/.
WORK = [
    ("/portrait-tattoos/", "Portraits"),
    ("/christian-tattoos/", "Christian pieces"),
    ("/script-tattoos/", "Script and lettering"),
    ("/walk-in-tattoos/", "Walk-ins and small pieces"),
    ("/tattoos/", "All my tattoos"),
]

TEMPLATE = (SRC / "template.html").read_text(encoding="utf-8")
# <!--photo file.jpg | alt text | extra classes -->   a gallery tile (third part optional)
PHOTO_RE = re.compile(r"<!--photo\s+(\S+)\s*\|\s*(.*?)\s*(?:\|\s*(.*?)\s*)?-->")
# <!--arch file.jpg | alt text | extra classes | extra attributes -->   a carved arch window
ARCH_RE = re.compile(r"<!--arch\s+(\S+)\s*\|\s*(.*?)\s*(?:\|\s*(.*?)\s*)?(?:\|\s*(.*?)\s*)?-->")
# The page head of a subject page: everything between its opening tag and its own closing
# tag, which sits at two-space indentation (the actions div inside it closes at four).
HEAD_RE = re.compile(r'(<div class="page-head">)(.*?)(\n  </div>\n)', re.S)

# The arch outline, closed all the way round: a violet edge, a faint inner edge, and a light catching the top left.
ARCH_SVG = ('<svg class="line" viewBox="0 0 100 150" preserveAspectRatio="none" aria-hidden="true">'
            '<path class="outer" d="M0,150 L0,51 C0,22.5 27,5.25 50,0 C73,5.25 100,22.5 100,51 L100,150 Z"/>'
            '<path class="inner" d="M3,147 L3,52 C3,26 28,9 50,4 C72,9 97,26 97,52 L97,147 Z"/>'
            '<path class="light" d="M0,150 L0,51 C0,22.5 27,5.25 50,0"/></svg>')


def arch_html(name, alt, classes="", attrs=""):
    cls = ("arch " + (classes or "")).strip()
    extra = (" " + attrs.strip()) if attrs else ""
    return (f'<figure class="{cls}"{extra}><img src="/images/{name}" alt="{esc(alt)}" '
            f'width="800" height="1200"><div class="recess"></div>{ARCH_SVG}</figure>')


def arch(m):
    name, alt, classes, attrs = m.group(1), m.group(2), m.group(3) or "", m.group(4) or ""
    return arch_html(name, alt, classes, attrs)


def head_art(body, meta):
    """Put the page's hero photo beside the heading, in a carved arch, when the meta block
    names one:  hero: file.jpg | alt text."""
    if "hero" not in meta:
        return body
    name, _, alt = meta["hero"].partition("|")
    fig = "\n    " + arch_html(name.strip(), alt.strip(), "head-art tilt", 'style="view-transition-name: vt-' + meta["path"].strip("/") + '"')
    return HEAD_RE.sub(
        lambda m: '<div class="page-head has-art">\n    <div class="head-copy">'
                  + m.group(2) + "\n    </div>" + fig + m.group(3),
        body, count=1)


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def photo(m):
    name, alt, extra = m.group(1), m.group(2), m.group(3) or ""
    if (OUT / "images" / name).exists():
        cls = ("reveal tilt " + extra).strip()
        return (f'<figure class="{cls}"><a class="open" href="/images/{name}">'
                f'<img src="/images/{name}" alt="{esc(alt)}" loading="lazy"></a>'
                f"<figcaption>{esc(alt)}</figcaption></figure>")
    return (f'<figure><div class="ph" role="img" aria-label="Photo to come: {esc(alt)}">'
            f"photo: images/{name}<br>alt: {esc(alt)}</div></figure>")


def ldjson(meta, url):
    page = {
        "@type": "WebPage",
        "@id": url,
        "url": url,
        "name": meta["title"],
        "description": meta["description"],
        "isPartOf": {"@id": WEBSITE_ID},
        "about": {"@id": PERSON_ID},
        "inLanguage": "en-GB",
    }
    graph = [STUDIO, PERSON, WEBSITE, page]
    if "service" in meta:
        service = {
            "@type": "Service",
            "@id": url + "#service",
            "name": meta["service"],
            "serviceType": meta["service"],
            "description": meta["description"],
            "provider": {"@id": PERSON_ID},
            "areaServed": AREA,
            "availableChannel": {
                "@type": "ServiceChannel",
                "serviceLocation": {"@id": STUDIO_ID},
                "serviceUrl": "https://www.truecolourstattoo.co.uk/quotation-booking-request",
            },
            "url": url,
        }
        page["mainEntity"] = {"@id": url + "#service"}
        graph.append(service)
    if meta["path"] != "/":
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Caitlin Carney Tattoo", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": meta.get("short", meta["title"].split("|")[0].strip()), "item": url},
            ],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)


def strip(path):
    items = []
    for href, label in WORK:
        cur = ' aria-current="page"' if href == path else ""
        items.append(f'      <li><a href="{href}"{cur}>{label}</a></li>')
    return ('  <nav class="strip" aria-label="Kinds of work">\n    <p>My work</p>\n    <ul>\n'
            + "\n".join(items) + "\n    </ul>\n  </nav>")


def page_meta(text):
    m = re.match(r"<!--meta\n(.*?)\n-->\n?", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta


def referenced_images():
    """Every image the pages refer to, as (page file name, image name): gallery photos,
    arches, each page's hero, and its share card (share-home.jpg when the page names none)."""
    refs = []
    for src in sorted((SRC / "pages").glob("*.html")):
        text = src.read_text(encoding="utf-8")
        meta = page_meta(text)
        names = [m[0] for m in PHOTO_RE.findall(text)] + [m[0] for m in ARCH_RE.findall(text)]
        if "hero" in meta:
            names.append(meta["hero"].partition("|")[0].strip())
        names.append(meta.get("og", "share-home.jpg"))
        refs.extend((src.name, name) for name in names)
    return refs


def build():
    if FINAL:
        missing = [(page, name) for page, name in referenced_images()
                   if not (OUT / "images" / name).exists()]
        if missing:
            sys.exit("Final build refused: missing images: "
                     + ", ".join(f"{page}: {name}" for page, name in missing))
    urls = []
    blanks = {}
    for src in sorted((SRC / "pages").glob("*.html")):
        text = src.read_text(encoding="utf-8")
        m = re.match(r"<!--meta\n(.*?)\n-->\n?", text, re.S)
        if not m:
            sys.exit(f"{src.name}: no meta block")
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = text[m.end():]
        body = PHOTO_RE.sub(photo, body)
        body = ARCH_RE.sub(arch, body)
        body = head_art(body, meta)
        path = meta["path"]
        url = SITE + path
        home = path == "/"
        if not home:
            # Inner pages: the photo section sits on a panel, and every section rises into view.
            body = body.replace('<section aria-labelledby="photos-h">',
                                '<section class="panel" aria-labelledby="photos-h">')
            body = re.sub(r'<section class="', '<section class="reveal ', body)
            body = re.sub(r'<section(?= [^>]*aria-labelledby)(?![^>]*class=)', '<section class="reveal"', body)

        slots = re.findall(r"\[[^\]]{2,}\]", body + meta["title"] + meta["description"])
        blanks[path] = slots

        if home:
            bar_left = '<span class="where">True Colours, 14 Guildhall Street, Preston</span>'
        else:
            bar_left = ('<a class="brand" href="/">Caitlin Carney Tattoo</a>'
                        '<span class="where">True Colours, Preston</span>')

        page = (TEMPLATE
                .replace("{{title}}", esc(meta["title"]))
                .replace("{{description}}", esc(meta["description"]))
                .replace("{{url}}", url)
                .replace("{{og_type}}", "website" if home else "article")
                .replace("{{og_image}}", SITE + "/images/" + meta.get("og", "share-home.jpg"))
                .replace("{{og_alt}}", esc(meta["title"]))
                .replace("{{ldjson}}", ldjson(meta, url))
                .replace("{{body_class}}", "home" if home else "inner")
                .replace("{{draft_banner}}", "" if FINAL else
                         '  <div class="draft-banner">Draft. Yellow means it needs Caitlin\'s words or a photo.</div>')
                .replace("{{bar_left}}", bar_left)
                .replace("{{cur_work}}", "")
                .replace("{{cur_prices}}", ' aria-current="page"' if path == "/prices/" else "")
                .replace("{{cur_about}}", ' aria-current="page"' if path == "/about/" else "")
                .replace("{{home_scripts}}", '  <script type="module" src="/assets/brush3d.js"></script>' if home else "")
                .replace("{{body}}", body.rstrip())
                .replace("{{strip}}", "" if home else strip(path)))

        # A stamp on the shared files, so a changed stylesheet or script is fetched at once
        # rather than served from a ten-minute cache
        for asset in ("/assets/site.css", "/assets/site.js", "/assets/brush3d.js"):
            page = page.replace(asset + '"', asset + "?v=" + STAMP + '"')
        out = OUT / ("index.html" if home else path.strip("/") + "/index.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8", newline="\n")
        urls.append((url, path))

    today = datetime.date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, path in sorted(urls, key=lambda u: (u[1] != "/", u[1])):
        sm += ["  <url>", f"    <loc>{url}</loc>", f"    <lastmod>{today}</lastmod>", "  </url>"]
    sm.append("</urlset>\n")
    (OUT / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8", newline="\n")

    total = sum(len(v) for v in blanks.values())
    for path, slots in blanks.items():
        print(f"{path:22} {len(slots):2} slots")
    print(f"{len(urls)} pages, {total} slots left, sitemap written")
    if FINAL and total:
        sys.exit("Final build refused: slots are still in the pages above.")


if __name__ == "__main__":
    build()
