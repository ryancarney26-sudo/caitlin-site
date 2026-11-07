"""Short emails from the robot, sent through Gmail with an app password. All optional: with no
mail secrets, send() does nothing and returns False, and the run log is the record.
"""
import os
from email.message import EmailMessage
from smtplib import SMTP_SSL

SITE_RECENT = "https://caitlincarneytattoo.co.uk/#recent"
REQUIRED = ("MAIL_FROM", "MAIL_APP_PASSWORD", "MAIL_TO")


def configured(env):
    return all(env.get(k) for k in REQUIRED)


def send(subject, body, env=None):
    env = os.environ if env is None else env
    if not configured(env):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Caitlin's site <{env['MAIL_FROM']}>"
    msg["To"] = ", ".join(a.strip() for a in env["MAIL_TO"].split(",") if a.strip())
    msg.set_content(body)
    with SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(env["MAIL_FROM"], env["MAIL_APP_PASSWORD"])
        smtp.send_message(msg)
    return True


def went_live(caption, permalink):
    subject = f"Going on the site: {caption}"
    body = (
        "This is going on the site within the hour:\n"
        "\n"
        f"{caption}\n"
        "\n"
        f"It will be here: {SITE_RECENT}\n"
        f"The Instagram post: {permalink}\n"
        "\n"
        "Wrong caption? Edit the caption on Instagram. The site follows within the hour.\n"
        "Don't want it on the site? Delete the post, or take the line out of the caption.\n"
    )
    return subject, body


def digest(items):
    lines = [
        "These posts from the last week have no line for the site, so they are not on it.",
        "Add one line to the caption that says what the tattoo is and where it sits,",
        "and it goes up within the hour.",
        "",
    ]
    for caption_start, permalink in items:
        lines.append(f"- {caption_start}")
        lines.append(f"  {permalink}")
    return "Posts without a line this week", "\n".join(lines) + "\n"


def needs_reconnect(reason):
    body = (
        "The site has stopped following Instagram.\n"
        f"Reason: {reason}\n"
        "\n"
        "To fix it, Caitlin taps allow again and Ryan runs connect.py.\n"
        "The steps are in the README under \"If it stops\".\n"
    )
    return "The site has stopped following Instagram", body
