"""One-off: connect Caitlin's Instagram to the robot. Run by Ryan, on his PC, inside the checkout.

    python -I _src\\instagram\\connect.py --link
        asks for the Meta App ID and prints the link Caitlin opens on her phone. She taps allow
        and lands on the site's /instagram-connect/ page, which shows a code to send to Ryan.

    python -I _src\\instagram\\connect.py
        asks for the App ID, the App Secret (typed hidden) and the code (or the whole address
        Caitlin sent). Turns the code into a 60-day token, encrypts it into
        _src/instagram/token.enc with a fresh key, stores the key as the repository secret
        IG_TOKEN_KEY through the gh command, and writes state.json. Nothing secret is printed.

Then commit and push _src/instagram/token.enc and _src/instagram/state.json.
"""
import argparse
import datetime
import getpass
import json
import pathlib
import subprocess
import sys
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from state import load_state, save_state       # noqa: E402
from tokenstore import encrypt_token, new_key  # noqa: E402

REDIRECT_URI = "https://caitlincarneytattoo.co.uk/instagram-connect/"
SCOPES = ("instagram_business_basic",             # her posts and photos, for the gallery
          "instagram_business_manage_insights")   # reach, saves and followers, for the Sunday numbers
SCOPE = ",".join(SCOPES)                           # both must be added on the Meta app first
REPO = "ryancarney26-sudo/caitlin-site"
AUTHORIZE = "https://www.instagram.com/oauth/authorize"
SHORT_TOKEN = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN = "https://graph.instagram.com/access_token"


def authorize_url(app_id):
    return AUTHORIZE + "?" + urlencode({"client_id": app_id, "redirect_uri": REDIRECT_URI,
                                        "response_type": "code", "scope": SCOPE})


def clean_code(s):
    s = s.strip()
    if "code=" in s:
        s = parse_qs(urlparse(s).query).get("code", [""])[0]
    return s.removesuffix("#_").strip()


def _http(url, data=None):
    req = Request(url, data=data, method="POST" if data is not None else "GET")
    with urlopen(req, timeout=30) as r:
        return r.read()


def exchange(app_id, app_secret, code, http=_http):
    """The code becomes a short-lived token, which becomes a 60-day one: (token, expires_in)."""
    body = urlencode({"client_id": app_id, "client_secret": app_secret,
                      "grant_type": "authorization_code", "redirect_uri": REDIRECT_URI,
                      "code": code}).encode("ascii")
    short = json.loads(http(SHORT_TOKEN, body))
    if "data" in short:
        short = short["data"][0]
    long_lived = json.loads(http(LONG_TOKEN + "?" + urlencode({
        "grant_type": "ig_exchange_token", "client_secret": app_secret,
        "access_token": short["access_token"]})))
    return long_lived["access_token"], int(long_lived.get("expires_in", 0))


def store(long_token, expires_in, now, repo_root, set_secret):
    folder = pathlib.Path(repo_root) / "_src" / "instagram"
    folder.mkdir(parents=True, exist_ok=True)
    key = new_key()
    (folder / "token.enc").write_bytes(encrypt_token(long_token, key))
    set_secret("IG_TOKEN_KEY", key)
    state = load_state(folder / "state.json")
    if not state.get("since"):                 # a reconnect keeps the switch-on date and the posts
        state["since"] = now.isoformat()
    state["token_refreshed"] = now.isoformat()
    state["token_expires"] = (now + datetime.timedelta(seconds=expires_in)).isoformat()
    save_state(folder / "state.json", state)


def gh_set_secret(name, value):
    subprocess.run(["gh", "secret", "set", name, "--repo", REPO], input=value, text=True, check=True)


def check_gh():
    """The code Caitlin sends works once. So gh must be known good before it is spent."""
    try:
        subprocess.run(["gh", "auth", "status"], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("gh is not installed or not signed in. Run: gh auth login")


APP_ID_PROMPT = "Instagram app ID (from the Instagram product's API setup page, not the Meta app ID): "


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--link", action="store_true", help="print the link for Caitlin and stop")
    args = ap.parse_args(argv)
    app_id = input(APP_ID_PROMPT).strip()
    if args.link:
        print()
        print("Send this link to Caitlin. She opens it on her phone, signed in to Instagram, and taps allow:")
        print(authorize_url(app_id))
        return 0
    check_gh()
    app_secret = getpass.getpass("Instagram app secret (typed hidden): ").strip()
    code = clean_code(input("The code, or the whole address Caitlin sent: "))
    token, expires_in = exchange(app_id, app_secret, code)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    store(token, expires_in, now, HERE.parent.parent, gh_set_secret)
    print("Connected. Token stored encrypted. Secret IG_TOKEN_KEY set.")
    print("Now commit and push _src/instagram/token.enc and _src/instagram/state.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
