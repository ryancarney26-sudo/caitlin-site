"""What the robot remembers between runs: state.json, committed with the site.

    since                 the switch-on moment; older posts are ignored
    token_refreshed       when the token was last refreshed (it lasts 60 days)
    token_expires         when the current token runs out
    posts                 Instagram post id -> what happened to it (live or removed)
    last_digest           when the weekly "posts without a line" email last went
"""
import copy
import json
import pathlib

STATE_FILE = pathlib.Path(__file__).with_name("state.json")
DEFAULTS = {
    "since": None,
    "token_refreshed": None,
    "token_expires": None,
    "posts": {},
    "last_digest": None,
}


def load_state(path):
    state = copy.deepcopy(DEFAULTS)
    if path is not None and pathlib.Path(path).exists():
        state.update(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
    return state


def save_state(path, state):
    text = json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    pathlib.Path(path).write_text(text, encoding="utf-8", newline="\n")
