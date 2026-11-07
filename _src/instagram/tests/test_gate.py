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


# Review findings, 7 Nov 2026: idioms, abbreviations, trailing bangs, everyday routing words.

def test_idioms_with_place_words_fail():
    for caption in ["Back in the studio Monday, come say hi",
                    "Back at it today with this little snake",
                    "Hands down my favourite piece this year",
                    "Welcome back to the studio everyone",
                    "Side note, I love doing snakes",
                    "Plenty of flash on hand this week, come in"]:
        assert site_caption(caption, RULES) is None, caption


def test_ambiguous_place_words_need_a_qualifier():
    assert site_caption("Twisty snake on the back", RULES) == "Twisty snake on the back"
    assert site_caption("Twisty snake, lower back", RULES) == "Twisty snake, lower back"
    assert site_caption("Small cross on her hand", RULES) == "Small cross on her hand"
    assert site_caption("Crowned crow on the back of the neck", RULES) == "Crowned crow on the back of the neck"
    assert site_caption("Little bee, hand piece", RULES) == "Little bee, hand piece"


def test_abbreviations_survive_the_sentence_split():
    assert site_caption("St. Michael the Archangel, forearm", RULES) == "St. Michael the Archangel, forearm"
    assert site_caption("Mr. Punch on the calf", RULES) == "Mr. Punch on the calf"
    assert site_caption("Big day. St. Michael the Archangel, forearm. More soon", RULES) == (
        "St. Michael the Archangel, forearm")


def test_whole_line_is_tried_last():
    assert site_caption("Portrait of a dad and his baby. Inner forearm", RULES) == (
        "Portrait of a dad and his baby. Inner forearm")


def test_trailing_exclamation_is_forgiven():
    assert site_caption("Loved doing this twisty snake on the forearm!", RULES) == (
        "Loved doing this twisty snake on the forearm")
    assert site_caption("Loved doing this twisty snake on the forearm!!", RULES) == (
        "Loved doing this twisty snake on the forearm")
    assert site_caption("Snake on the forearm! Come and get one", RULES) is None


def test_routing_ignores_everyday_words():
    assert pages_for("God I loved this one, inner forearm", RULES) == []
    assert pages_for("Cat skull, forearm", RULES) == []
    assert pages_for("Date night, forearm", RULES) == []
    assert pages_for("Lamb of God, forearm", RULES) == ["13-christian-tattoos.html"]
