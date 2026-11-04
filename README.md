# Caitlin Carney Tattoo

Static site. The files in this folder are the whole site: plain HTML, one shared stylesheet
in `assets/site.css`, no JavaScript.

## Branches

- `main` is what GitHub Pages serves at caitlincarneytattoo.co.uk. Only facts we are sure of.
- `v2-subjects` is the **nine-page draft** built around the search map: home, one page per kind
  of work (portraits, Christian pieces, script, memorial, walk-ins), prices, where clients come
  from, and about. Yellow slots mark what still needs Caitlin's words, a price or a photo.
  It merges into `main` once the slots are filled and Caitlin has approved it.

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

## Photos, when they arrive

Put them in an `images/` folder with these names, and switch to the full draft:

- `work-01.jpg` to `work-12.jpg`: finished work, healed where possible, portrait crops (4:5).
- `style-one.jpg` and `style-two.jpg`: one strong example of each style, landscape (4:3).
- `caitlin.jpg`: a portrait at her station.

Then edit each image's `alt` text so it says what the tattoo is. Google reads alt text and file names.
Keep each file under about 400 KB (export at 1600px on the long side, quality 80).

## After the site is live

- Open `https://caitlincarneytattoo.co.uk/robots.txt` and check the Allow lines show.
- Add the site to Google Search Console and Bing Webmaster Tools, and submit `sitemap.xml`.
- Create Caitlin's Google Business Profile: name "Caitlin Carney Tattoo", address 14 Guildhall Street,
  website this domain. Verification can take days, so start it early.
- Put the domain in the Instagram bio link.
