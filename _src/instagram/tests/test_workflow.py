"""The robot's schedule (8 Nov 2026, Ryan: "only needs to check once a day"): every evening, with
backup tries later the same evening because GitHub drops scheduled runs. A backup that finds nothing
new does nothing."""
import pathlib
import re

WORKFLOW = pathlib.Path(__file__).resolve().parents[3] / ".github" / "workflows" / "instagram.yml"


def crons():
    return re.findall(r'cron:\s*"([^"]+)"', WORKFLOW.read_text(encoding="utf-8"))


def test_each_trigger_fires_once_a_day():
    assert crons(), "the robot has no schedule"
    for cron in crons():
        minute, hour, day, month, weekday = cron.split()
        assert minute.isdigit() and hour.isdigit(), cron
        assert (day, month, weekday) == ("*", "*", "*"), cron
        assert int(minute) not in (0, 59), cron            # GitHub is busiest on the hour


def test_one_evening_run_and_at_most_two_backups():
    hours = sorted(int(c.split()[1]) for c in crons())
    assert 1 <= len(hours) <= 3
    assert all(17 <= h <= 23 for h in hours)              # evenings, UK time
