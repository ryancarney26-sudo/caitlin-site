"""The few calls the robot makes to Meta's Instagram API (Instagram API with Instagram Login).

    Api(token).fetch_media()        the latest posts, newest first
    Api(token).media_exists(id)     False once a post has been deleted
    Api(token).refresh()            a fresh 60-day token
    Api(token).download(url)        the bytes of a photo from Instagram's CDN

Errors come back as ApiError; is_auth says the token is the problem.
"""
import datetime
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

GRAPH = "https://graph.instagram.com/v26.0"
REFRESH = "https://graph.instagram.com/refresh_access_token"
MEDIA_FIELDS = "id,caption,media_type,media_url,permalink,timestamp,children{id,media_type,media_url}"
TIMEOUT = 30


class ApiError(Exception):
    def __init__(self, message, code=None, subcode=None, error_type=None, status=None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.error_type = error_type
        self.status = status

    @property
    def is_auth(self):
        return self.code == 190 or self.error_type == "OAuthException" or self.status == 401


def _get_json(url):
    try:
        with urlopen(url, timeout=TIMEOUT) as r:
            body = r.read()
    except HTTPError as e:
        body = e.read()
        try:
            err = json.loads(body).get("error", {})
        except ValueError:
            err = {}
        raise ApiError(err.get("message", f"HTTP {e.code}"), err.get("code"),
                       err.get("error_subcode"), err.get("type"), e.code) from None
    return json.loads(body)


class Api:
    def __init__(self, token):
        self.token = token

    def _url(self, path, **params):
        params["access_token"] = self.token
        return f"{GRAPH}/{path}?{urlencode(params)}"

    def fetch_media(self, limit=25):
        return _get_json(self._url("me/media", fields=MEDIA_FIELDS, limit=limit)).get("data", [])

    def fetch_media_since(self, since, limit=50, max_pages=40):
        """Every post back to `since` (an aware datetime), newest first, a page at a time."""
        out, after = [], None
        for _ in range(max_pages):
            params = {"fields": MEDIA_FIELDS, "limit": limit}
            if after:
                params["after"] = after
            page = _get_json(self._url("me/media", **params))
            data = page.get("data", [])
            for m in data:
                if parse_timestamp(m["timestamp"]) < since:
                    return out
                out.append(m)
            paging = page.get("paging", {})
            after = paging.get("cursors", {}).get("after")
            if not data or not paging.get("next") or not after:
                return out
        return out

    def media_exists(self, media_id):
        try:
            _get_json(self._url(media_id, fields="id"))
            return True
        except ApiError as e:
            if e.code == 100 and (e.subcode == 33 or "does not exist" in str(e)):
                return False
            raise

    def refresh(self):
        data = _get_json(REFRESH + "?" + urlencode({"grant_type": "ig_refresh_token",
                                                   "access_token": self.token}))
        return data["access_token"], int(data.get("expires_in", 0))

    def download(self, url):
        with urlopen(url, timeout=TIMEOUT) as r:
            return r.read()


def parse_timestamp(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
