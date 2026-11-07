"""The caption gate: one plain line, in her words, that says what it is and where it sits."""
import pathlib

from gate import load_rules, pages_for, site_caption

RULES = load_rules(pathlib.Path(__file__).resolve().parents[1] / "rules.json")

# Her real captions from 6 November, 4 November and 26 October 2026.
SNAKE = "Had a lot of fun doing this twisty snake from my flash 😝🐍"
SNAKE_PLACED = "Had a lot of fun doing this twisty snake from my flash, on the forearm 😝🐍"
PROMO = ("🙌Colour realism for less £ than a night out???🙌 I always thought before getting into "
         "tattooing that I wanted to focus purely on black and grey work, but since I started "
         "painting and using colour in my art away from tattooing I realised how much I enjoyed it")
EVENT = ("Insane weekend so happy to have attended @halloweentattoobash thank you so much "
         "@ryancarney22 for putting up with me stabbing you all weekend")


def test_real_caption_without_place_fails():
    assert site_caption(SNAKE, RULES) is None


def test_real_caption_with_place_passes():
    assert site_caption(SNAKE_PLACED, RULES) == (
        "Had a lot of fun doing this twisty snake from my flash, on the forearm")


def test_promo_fails():
    assert site_caption(PROMO, RULES) is None


def test_event_fails():
    assert site_caption(EVENT, RULES) is None


def test_line_anywhere_in_caption():
    caption = "Loved this one 😝\nTwisty snake from my flash, on the forearm.\n#tattoo #preston"
    assert site_caption(caption, RULES) == "Twisty snake from my flash, on the forearm"


def test_sentence_inside_a_line():
    caption = "Big day. Twisty snake from my flash, on the forearm. More soon"
    assert site_caption(caption, RULES) == "Twisty snake from my flash, on the forearm"


def test_hashtag_on_the_line_rejects_it():
    assert site_caption("Snake on the forearm #tattoo", RULES) is None


def test_banned_word():
    assert site_caption("DM me for a snake on the forearm", RULES) is None


def test_too_short():
    assert site_caption("Forearm snake", RULES) is None


def test_too_long():
    assert site_caption(" ".join(["word"] * 18) + " on the forearm", RULES) is None   # 21 words
    assert site_caption(" ".join(["word"] * 17) + " on the forearm", RULES) is not None  # 20 words


def test_capitalises_first_letter():
    assert site_caption("twisty snake, upper arm", RULES) == "Twisty snake, upper arm"


def test_place_must_be_whole_word():
    assert site_caption("Knight in armour from my flash sheet", RULES) is None
    assert site_caption("Knight in armour, chest piece", RULES) == "Knight in armour, chest piece"


def test_drops_pipe_and_angle_brackets():
    assert site_caption("Twisty snake | on the forearm", RULES) == "Twisty snake on the forearm"
    assert site_caption("Snake <3 on the forearm", RULES) == "Snake 3 on the forearm"
    assert "-->" not in (site_caption("Snake --> on the forearm", RULES) or "")


def test_empty():
    assert site_caption(None, RULES) is None
    assert site_caption("", RULES) is None


def test_pages_for():
    assert pages_for("Portrait of a dad and his baby, black and grey, inner forearm", RULES) == [
        "10-portrait-tattoos.html"]


def test_pages_for_two():
    assert pages_for("Psalm 23 in script, forearm", RULES) == [
        "12-script-tattoos.html", "13-christian-tattoos.html"]


def test_pages_for_flash_is_a_walk_in():
    assert pages_for("Twisty snake from my flash, on the forearm", RULES) == ["15-walk-in-tattoos.html"]


def test_pages_for_none():
    assert pages_for("Compass in black and grey, upper arm", RULES) == []
