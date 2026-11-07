# Caitlin Carney Tattoo

Static site. The files in this folder are the whole site: plain HTML, one shared stylesheet
in `assets/site.css`, and one small inline script in every page (from `../site-src/template.html`)
that does the motion: sections rising into view, the glow that follows the pointer, the drifting
dust, the tilting frames. All of it switches off when a visitor's device asks for reduced motion.

Design, since 7 November 2026: "night studio". Dark pages with a violet plaster texture, bone-white
type, Grenze Gotisch for headings, Atkinson Hyperlegible for reading, and photos set in pointed
arches. Page bodies write a photo-in-an-arch as `<!--arch file.jpg | alt | classes | attributes-->`
and a gallery tile as `<!--photo file.jpg | alt | classes-->`; `make.py` turns both into markup.

## Branches

- `main` is what GitHub Pages serves at caitlincarneytattoo.co.uk: the **eight-page site**, live
  since 5 November 2026. Home, one page per kind of work (portraits, Christian pieces, script,
  walk-ins), prices, where clients come from, and about. Only facts we are sure of.
- `v2-subjects` was the draft branch for those pages and is level with `main` now. Draft the next
  round there, or on a new branch, so `main` only ever gets finished pages. Yellow slots mark what
  still needs Caitlin's words, a price or a photo, and `--final` refuses to build while any remain.

## How the pages are made

The page bodies live outside this repo in `../site-src/pages/`, one file per page with a small
meta block at the top. `python ../site-src/make.py` stamps the shared head, header and footer
onto each one, writes the finished HTML here, and rewrites `sitemap.xml`. It prints how many
yellow slots are left. `python ../site-src/make.py --final` refuses to build while any slot remains
and drops the draft banner.

Photos: drop them into `images/` with the file names written in the page bodies (for example
`portrait-tattoo-preston-01.jpg`), run the build again, and the placeholders become real images.
Export at 1600px on the long side, quality 80, under about 400 KB each. Portrait crops (4:5).

- `CNAME` tells GitHub Pages the domain. Leave it alone.
- `google42e6e428d1cd23fe.html` is Google Search Console's proof that we own the site. Leave it alone too.

## Put it online (GitHub Pages, free)

1. On GitHub, create a new **public** repository called `caitlin-site`. No README, no licence.
2. Push this folder to it:

       git remote add origin https://github.com/ryancarney26-sudo/caitlin-site.git
       git push -u origin main

3. In the repository: **Settings, Pages**. Source: "Deploy from a branch". Branch `main`, folder `/ (root)`. Save.
4. Still on that page, **Custom domain**: type `caitlincarneytattoo.co.uk` and save.
   It will say "DNS check unsuccessful" until the records below exist. That is normal.
5. Once DNS has gone through, tick **Enforce HTTPS**. The certificate can take up to an hour to appear.

## DNS records to add at GoDaddy

GoDaddy: My Products, the domain, **DNS**. Delete the "Parked" A record GoDaddy adds by default,
then add these. Leave TTL at the default.

| Type  | Name | Value                      |
|-------|------|----------------------------|
| A     | @    | 185.199.108.153            |
| A     | @    | 185.199.109.153            |
| A     | @    | 185.199.110.153            |
| A     | @    | 185.199.111.153            |
| CNAME | www  | `ryancarney26-sudo.github.io`     |

Replace `ryancarney26-sudo` with the GitHub username that owns the repository.
These four addresses are GitHub Pages' published ones. Changes usually show within an hour.

Do **not** switch the domain's nameservers to Cloudflare. New Cloudflare domains block AI crawlers
by default, and the whole point of this site is to be read by them.

## Photos

Photos live in `images/`, named by subject with the place in the file name (for example
`portrait-tattoo-preston-01.jpg`, `christian-tattoo-preston-02.jpg`, `tattoo-preston-medusa.jpg`).
Each page body lists its photos as one-line comments with a caption, which doubles as the alt text,
so say what the tattoo is and where it sits. To add one: drop the file in `images/`, add a photo
line to the page body in `../site-src/pages/`, and rebuild. Keep files under about 400 KB
(1400px on the long side, quality 85, metadata stripped).

Still wanted: `caitlin-carney-tattoo-artist-preston.jpg`, a portrait of Caitlin at her station,
for the about page.

## After the site is live

- Open `https://caitlincarneytattoo.co.uk/robots.txt` and check the Allow lines show.
- Add the site to Google Search Console and Bing Webmaster Tools, and submit `sitemap.xml`.
- Create Caitlin's Google Business Profile: name "Caitlin Carney Tattoo", address 14 Guildhall Street,
  website this domain. Verification can take days, so start it early.
- Put the domain in the Instagram bio link.
