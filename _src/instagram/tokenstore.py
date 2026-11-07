"""The Instagram access token, kept in the repository encrypted.

The workflow cannot write Actions secrets, but it must store the refreshed token somewhere.
So the token lives in token.enc, encrypted with a key that is the only secret (IG_TOKEN_KEY).
"""
import pathlib

from cryptography.fernet import Fernet, InvalidToken

TOKEN_FILE = pathlib.Path(__file__).with_name("token.enc")


class TokenError(Exception):
    pass


def new_key():
    return Fernet.generate_key().decode("ascii")


def encrypt_token(token, key):
    return Fernet(key.encode("ascii")).encrypt(token.encode("utf-8"))


def decrypt_token(blob, key):
    try:
        return Fernet(key.encode("ascii")).decrypt(blob).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as e:
        raise TokenError("the token file cannot be read with this key") from e
