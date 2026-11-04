# Caitlin Carney Tattoo, one-page site

Static site. No build step. The files in this folder are the whole site.

- `index.html` is the **launch version**: only facts we are sure of, no placeholders.
- The **full draft** with the gallery, the two style sections, prices and the portrait is kept
  outside this folder in `../site-drafts/index-full.html`. It replaces `index.html` once Caitlin
  has supplied her styles, prices, days and photos. Search that file for `[` to find every blank.
- `CNAME` tells GitHub Pages the domain. Leave it alone.

## Put it online (GitHub Pages, free)

1. On GitHub, create a new **public** repository called `caitlin-site`. No README, no licence.
2. Push this folder to it:

       git remote add origin https://github.com/<username>/caitlin-site.git
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
| CNAME | www  | `<username>.github.io`     |

Replace `<username>` with the GitHub username that owns the repository.
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
