# Caitlin Carney Tattoo

Static site. The files in this folder are the whole site: plain HTML, one shared stylesheet
in `assets/site.css`, and one small inline script in every page (from `_src/template.html`)
that does the motion: sections rising into view, the glow that follows the pointer, the drifting
dust, the tilting frames. All of it switches off when a visitor's device asks for reduced motion.

New tattoos arrive by themselves: Caitlin posts to Instagram, and a robot on GitHub puts the
photo on the site that evening. See **New photos from Instagram** below.

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

**Post the tattoo on Instagram as normal. That's all.**
That evening it is on the site. Claude looks at the photo and writes a short, plain caption:
what the tattoo shows, its style, and where it sits.
Posts that aren't a finished tattoo stay off: offers, events, flash sheets, selfies.
Videos never go up. Posts from before 6 November 2026 are left alone.
Once the emails are set up, you get one each time a photo goes up, with its caption.

**If Claude gets a caption wrong,** add one line to the Instagram caption that says what it is and
where it sits. For example: **Twisty snake from my flash, on the forearm.**
Your line replaces Claude's by the next evening. Keep it plain: no hashtags, @names, prices or question marks.
**If a tattoo was kept off by mistake,** add a line the same way, and it goes up.
**To take a photo off the site,** delete the post, or ask Ryan.
On Sunday evening an email lists the week's posts that were kept off.

### How it works (for Ryan)

Every evening at 19:23 UTC (7:23pm in winter, 8:23pm in summer), GitHub runs the workflow
**Instagram photos** (`.github/workflows/instagram.yml`). GitHub sometimes skips a scheduled run,
so it tries again at 21:23 and 23:23; a try that finds nothing new changes nothing. It asks Instagram for Caitlin's latest 25 posts. For each
new photo post it downloads the photo, turns it upright, shrinks it to at most 1400px, compresses
it under 400 KB, and strips every scrap of metadata. Then it picks the caption:

- **Her line, if her caption has one.** The subject pages come from its words (`rules.json`).
- **Otherwise Claude's** (`describe.py`, Claude Opus 5.5). Claude says whether the photo is a
  finished tattoo, writes one plain line, and picks the subject pages. A post that isn't a finished
  tattoo is kept off and remembered in `state.json`, so Claude is never asked twice about it.
  About 2p a photo. At most 10 look-ups a run (`max_claude_per_run` in `rules.json`).

It adds the photo to the top of "Recent work" on the home page (the oldest drops off after twelve)
and to its subject pages, rebuilds with `--final`, commits to `main`, and GitHub Pages publishes.
If the build fails, nothing is committed and GitHub emails you.

Her line, added or edited, replaces the caption by the next evening. Taking her line out hands the
caption back to Claude; the photo stays. A deleted post comes off at the next evening run. Without the Claude key, only posts with her line go up, as before 7 November 2026.
Photos from Instagram come at 1080px on the long side, a little smaller than hand-exported ones.

The robot's files are in `_src/instagram/`:

- `sync.py` is the evening run. `connect.py` is the one-off connection.
- `gate.py` finds her line. `describe.py` asks Claude about a photo. `gallery.py` edits the
  photo lines. `images.py` shrinks photos.
- `api.py` talks to Instagram. `mail.py` sends the emails. `tokenstore.py` keeps the key safe.
- `rules.json` holds the body words, the banned words, the subject-page words, and how many
  photos "Recent work" keeps. Edit it and push; no code change needed.
- `state.json` remembers which posts are on the site. `token.enc` is the Instagram key,
  encrypted. Both are committed by the robot. Nothing secret is in the clear.
- `export.py` is the one-off export of older posts, for a backfill (see below).
- `tests/` are the tests. Run them with `python -m pytest _src/instagram/tests -q`.

### All my tattoos, and the backfill of older posts

The page `/tattoos/` (`_src/pages/17-tattoos.html`) shows every photo on the site, newest first.
The robot adds each new photo there too, as well as to "Recent work" and its subject pages.

On 7 November 2026 her Instagram posts from 7 May to 5 November were backfilled. The
**Instagram export** workflow (Actions, Run workflow, a start date) downloaded them for a day.
Claude looked at each photo, decided whether it was a finished tattoo, wrote its caption and picked
its subject pages. A second Claude checked every one, and the photos were compared by eye with
those already on the site, so nothing appears twice. Older photos went on their subject pages and
on "All my tattoos", not on the home page. Every post is remembered in `state.json`, so the robot
never adds one again. The robot doesn't follow caption edits on posts from before 6 November, so to
change one of those captions, edit its line in the page body in `_src/pages/` and rebuild.

### Secrets (repository settings, Actions)

Set each one yourself with `gh secret set NAME` and type the value when asked.

- `IG_TOKEN_KEY`: the key that unlocks `token.enc`. `connect.py` sets this one for you.
- `ANTHROPIC_API_KEY`: the key Claude's captions need. Make it on your own Anthropic account
  (console.anthropic.com, API keys), buy a few pounds of credit, and set a monthly spend limit
  of about $5 on the limits page, so nothing can run away. Without it, only posts with her line go up.
- `MAIL_FROM`: your Gmail address. `MAIL_APP_PASSWORD`: an app password for it (Google
  account, Security, 2-Step Verification, App passwords). `MAIL_TO`: who gets the emails,
  comma-separated. Without these three, no emails are sent and the run log is the record.

### Connecting it (once)

1. Caitlin's Instagram must be a **professional account** (Creator or Business). In the
   Instagram app: Settings, Account type and tools, Switch to professional account. Free.
2. At developers.facebook.com, sign in with Facebook and create an app. Add the **Instagram**
   product and choose the set-up with Instagram login. On the app's permissions page, add
   **three** permissions: `instagram_business_basic`, `instagram_business_manage_insights`
   and `instagram_business_manage_comments`. The second lets the robot read reach and saves,
   for the weekly numbers email. The third lets it read comments, for the Sunday review asks.
   If one is missing, Instagram shows an error when Caitlin opens the link.
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
without changing anything. A dry run asks Claude about new posts too, so it costs a few pence.

Tick **check Claude** instead to ask Claude about three photos already on the site and print what
it says. It changes nothing and costs about 6p. Use it once after setting `ANTHROPIC_API_KEY`.

### If it stops

- **GitHub pauses the evening job** after 60 days without activity in the repository. The workflow
  page shows a banner. Click **Enable workflow**. The robot catches up on its next run.
- **The run says "Not connected yet."** Nothing is wrong. The robot waits quietly until
  Connecting it is done.
- **The run says "The Instagram connection needs setting up again."** The key has lapsed: the robot
  was off for more than 60 days, or Caitlin changed her password or removed the app. Do steps
  5 to 7 of Connecting it again. The switch-on date and the photos already up are kept.
  The run fails (and GitHub emails you) once a day, at the evening run; the backup tries that
  evening stay quiet, so a lapse does not flood your inbox.
- **The log says "Claude: ... HTTP 401" or "HTTP 403".** The Anthropic key is wrong, or out of
  credit. New posts wait, and go up at the next evening run once the key works again.
- **The build failed.** GitHub emails you. The log names the missing image or the open slot.
- **A wrong photo or caption went up.** Caitlin edits or deletes the post. The site follows at the
  next evening run.

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
