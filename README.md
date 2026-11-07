# Caitlin Carney Tattoo

Static site. The files in this folder are the whole site: plain HTML, one shared stylesheet
in `assets/site.css`, and one small inline script in every page (from `_src/template.html`)
that does the motion: sections rising into view, the glow that follows the pointer, the drifting
dust, the tilting frames. All of it switches off when a visitor's device asks for reduced motion.

New tattoos arrive by themselves: Caitlin posts to Instagram, and a robot on GitHub puts the
photo on the site within the hour. See **New photos from Instagram** below.

Design, since 7 November 2026: "night studio". Dark pages with a violet plaster texture, bone-white
type, Grenze Gotisch for headings, Atkinson Hyperlegible for reading, and photos set in pointed
arches. Page bodies write a photo-in-an-arch as `<!--arch file.jpg | alt | classes | attributes-->`
and a gallery tile as `<!--photo file.jpg | alt | classes-->`; `make.py` turns both into markup.
A gallery tile opens full size in a lightbox (arrows, swipe, Escape, and a "Get a quote" button),
and every page carries a share card, `images/share-*.jpg`, so a link sent on WhatsApp or Instagram
shows a picture. The cards are rendered at 1200 by 630 from `_src/share-card.html`; a page
picks its own with an `og: share-portraits.jpg` line in its meta block, else it gets `share-home.jpg`.

## Branches

- `main` is what GitHub Pages serves at caitlincarneytattoo.co.uk: the **eight-page site**, live
  since 5 November 2026. Home, one page per kind of work (portraits, Christian pieces, script,
  walk-ins), prices, where clients come from, and about. Only facts we are sure of.
- `v2-subjects` was the draft branch for those pages and is level with `main` now. Draft the next
  round there, or on a new branch, so `main` only ever gets finished pages. Yellow slots mark what
  still needs Caitlin's words, a price or a photo, and `--final` refuses to build while any remain.

## How the pages are made

The page bodies live in `_src/pages/`, one file per page with a small meta block at the top.
The folder's name starts with an underscore so GitHub Pages leaves it out of the published site.
Do not add a `.nojekyll` file: that would publish it.

From this folder, `python -I _src\make.py` stamps the shared head, header and footer onto each
page, writes the finished HTML here, and rewrites `sitemap.xml`. It prints how many yellow slots
are left. `python -I _src\make.py --final` refuses to build while any slot remains, refuses if
any photo a page names is missing from `images/`, and drops the draft banner.

Photos: drop them into `images/` with the file names written in the page bodies (for example
`portrait-tattoo-preston-01.jpg`), run the build again, and the placeholders become real images.
Export at 1400px on the long side, quality 85, under about 400 KB each, metadata stripped.
Portrait crops (4:5) suit the gallery best, but any shape works.

- `CNAME` tells GitHub Pages the domain. Leave it alone.
- `google42e6e428d1cd23fe.html` is Google Search Console's proof that we own the site. Leave it alone too.
- `instagram-connect/` is the page Instagram sends Caitlin to when she connects. Leave it alone.

## New photos from Instagram

### Putting a tattoo on the site (for Caitlin)

Post the tattoo on Instagram as normal.
Somewhere in the caption, write **one line that says what it is and where it sits.**
For example: **Twisty snake from my flash, on the forearm.**

Keep that line short and plain. No hashtags, no @names, no prices, no question marks on that line.
An exclamation mark at the end is fine. "Forearm" is clearer than "arm"; "on the back" is clearer than "back".
The rest of the caption can be as chatty as you like. It is not used.
The photo is on the site within the hour, with that line as its caption.

To change the caption, edit the post. The site follows within the hour.
To take a photo off the site, delete the post, or take the line out of the caption.
Videos never go up. Posts from before the day we connected never go up.
If a post has no line, nothing happens. On Sunday evening an email lists the week's posts without one.

### How it works (for Ryan)

Every hour, at 17 minutes past, GitHub runs the workflow **Instagram photos**
(`.github/workflows/instagram.yml`). It asks Instagram for Caitlin's latest 25 posts. For each
photo post with a usable line, it downloads the photo, turns it upright, shrinks it to at most
1400px, compresses it under 400 KB, strips every scrap of metadata, and adds it to the top of
"Recent work" on the home page (the oldest drops off after twelve) and to any subject page whose
words match the line. Then it rebuilds with `--final`, commits to `main`, and GitHub Pages
publishes. If the build fails, nothing is committed and GitHub emails you.

An edited caption updates the site. A deleted post, or a line taken out, removes the photo.
Once a day, on the 04:17 run, it checks that every photo it put up is still on Instagram.
Photos from Instagram come at 1080px on the long side, a little smaller than hand-exported ones.

The robot's files are in `_src/instagram/`:

- `sync.py` is the hourly run. `connect.py` is the one-off connection.
- `gate.py` finds the one line. `gallery.py` edits the photo lines. `images.py` shrinks photos.
- `api.py` talks to Instagram. `mail.py` sends the emails. `tokenstore.py` keeps the key safe.
- `rules.json` holds the body words, the banned words, the subject-page words, and how many
  photos "Recent work" keeps. Edit it and push; no code change needed.
- `state.json` remembers which posts are on the site. `token.enc` is the Instagram key,
  encrypted. Both are committed by the robot. Nothing secret is in the clear.
- `tests/` are the tests. Run them with `python -m pytest _src/instagram/tests -q`.

### Secrets (repository settings, Actions)

Set each one yourself with `gh secret set NAME` and type the value when asked.

- `IG_TOKEN_KEY`: the key that unlocks `token.enc`. `connect.py` sets this one for you.
- `MAIL_FROM`: your Gmail address. `MAIL_APP_PASSWORD`: an app password for it (Google
  account, Security, 2-Step Verification, App passwords). `MAIL_TO`: who gets the emails,
  comma-separated. Without these three, no emails are sent and the run log is the record.

### Connecting it (once)

1. Caitlin's Instagram must be a **professional account** (Creator or Business). In the
   Instagram app: Settings, Account type and tools, Switch to professional account. Free.
2. At developers.facebook.com, sign in with Facebook and create an app. Add the **Instagram**
   product and choose the set-up with Instagram login.
3. In the app's Instagram settings, under business login, add the redirect URI
   `https://caitlincarneytattoo.co.uk/instagram-connect/`. If the form also asks for a
   deauthorize address or a data deletion address, use that same address. Note the
   **Instagram app ID** and **Instagram app secret** shown on that page. They are not the
   Meta app ID at the top of the dashboard.
4. Under app roles, add Caitlin's Instagram account as a tester. She accepts in the Instagram
   app: Settings, Website permissions (also called Apps and websites), Tester invites.
5. On this PC, `gh` must be installed and signed in (`gh auth status` says so; `gh auth login`
   if not). Then, in this folder, run `python -I _src\instagram\connect.py --link`, type the
   Instagram app ID, and send Caitlin the link. She opens it on her phone, signed in to
   Instagram, and taps allow. The site's connect page shows her a code. She sends it to you.
   It lasts an hour and works once.
6. Run `python -I _src\instagram\connect.py` and paste the Instagram app ID, the Instagram app
   secret (typed hidden) and the code. It stores the key encrypted, sets the secret, and
   writes `state.json`.
7. Commit and push: `git add _src/instagram/token.enc _src/instagram/state.json`, then commit, then push.
8. On GitHub: Actions, Instagram photos, Run workflow, tick **dry run**, and read the log.
   It should list her recent posts and say "skip" for each one without a line.
   Then run it again without the tick.

### Running it by hand

GitHub, Actions, **Instagram photos**, Run workflow. Tick **dry run** to see what it would do
without changing anything.

### If it stops

- **GitHub pauses the hourly job** after 60 days without activity in the repository. The workflow
  page shows a banner. Click **Enable workflow**. The robot catches up on its next run.
- **The run says "Not connected yet."** Nothing is wrong. The robot waits quietly until
  Connecting it is done.
- **The run says "The Instagram connection needs setting up again."** The key has lapsed: the robot
  was off for more than 60 days, or Caitlin changed her password or removed the app. Do steps
  5 to 7 of Connecting it again. The switch-on date and the photos already up are kept.
  The log says this every hour, but the run only fails (and GitHub only emails you) once a day,
  on the 08:17 run, so a lapse does not flood your inbox. Times are UTC.
- **The build failed.** GitHub emails you. The log names the missing image or the open slot.
- **A wrong photo or caption went up.** Caitlin edits or deletes the post. The site follows within
  the hour, or within a day for a deleted post.

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
The robot names its own `tattoo-preston-<words from the caption>-<date>.jpg`.
Each page body lists its photos as one-line comments with a caption, which doubles as the alt text,
so say what the tattoo is and where it sits. To add one by hand: drop the file in `images/`, add a
photo line to the page body in `_src/pages/`, and rebuild. Keep files under about 400 KB
(1400px on the long side, quality 85, metadata stripped).

Still wanted: `caitlin-carney-tattoo-artist-preston.jpg`, a portrait of Caitlin at her station,
for the about page.

## After the site is live

- Open `https://caitlincarneytattoo.co.uk/robots.txt` and check the Allow lines show.
- Add the site to Google Search Console and Bing Webmaster Tools, and submit `sitemap.xml`.
- Create Caitlin's Google Business Profile: name "Caitlin Carney Tattoo", address 14 Guildhall Street,
  website this domain. Verification can take days, so start it early.
- Put the domain in the Instagram bio link.
