"""Mail is optional: nothing is sent without the three mail secrets. With them, Gmail over SSL."""
import mail
from mail import configured, digest, needs_reconnect, send, went_live

ENV = {"MAIL_FROM": "ryan@example.com", "MAIL_APP_PASSWORD": "app-pw",
       "MAIL_TO": "caitlin@example.com, ryan@example.com"}


class FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host, self.port = host, port
        self.logins, self.sent = [], []
        FakeSMTP.instances.append(self)

    def login(self, user, password):
        self.logins.append((user, password))

    def send_message(self, msg):
        self.sent.append(msg)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_configured():
    assert configured(ENV)
    assert not configured({})
    assert not configured({**ENV, "MAIL_TO": ""})


def test_not_configured_sends_nothing(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(mail, "SMTP_SSL", FakeSMTP)
    assert send("Subject", "Body", env={}) is False
    assert FakeSMTP.instances == []


def test_send_logs_in_and_sends(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(mail, "SMTP_SSL", FakeSMTP)
    assert send("On the site: Twisty snake, forearm", "Body line.\nhttps://x/", env=ENV) is True
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.gmail.com", 465)
    assert smtp.logins == [("ryan@example.com", "app-pw")]
    msg = smtp.sent[0]
    assert msg["Subject"] == "On the site: Twisty snake, forearm"
    assert msg["To"] == "caitlin@example.com, ryan@example.com"
    assert "ryan@example.com" in msg["From"]
    assert "https://x/" in msg.get_content()


def test_went_live_copy():
    subject, body = went_live("Twisty snake, forearm", "https://www.instagram.com/p/abc/")
    assert subject == "Going on the site: Twisty snake, forearm"
    assert "within the hour" in body
    assert "I've put this on the site" not in body       # the build and push come after this email
    assert "https://www.instagram.com/p/abc/" in body
    assert "https://caitlincarneytattoo.co.uk/#recent" in body
    assert "Edit the caption" in body


def test_digest_copy():
    subject, body = digest([("Had a lot of fun doing this twisty snake", "https://www.instagram.com/p/a/")])
    assert subject == "Posts without a line this week"
    assert "https://www.instagram.com/p/a/" in body and "twisty snake" in body


def test_needs_reconnect_copy():
    subject, body = needs_reconnect("the key no longer works")
    assert subject == "The site has stopped following Instagram"
    assert "connect.py" in body and "the key no longer works" in body
