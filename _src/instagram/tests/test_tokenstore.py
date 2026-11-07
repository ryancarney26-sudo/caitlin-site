"""The Instagram token lives in the repository encrypted; only the key is a secret."""
import pytest

from tokenstore import TokenError, decrypt_token, encrypt_token, new_key


def test_round_trip():
    key = new_key()
    assert decrypt_token(encrypt_token("IGAAxTokenValue", key), key) == "IGAAxTokenValue"


def test_blob_does_not_contain_the_token():
    assert b"IGAAxTokenValue" not in encrypt_token("IGAAxTokenValue", new_key())


def test_wrong_key():
    with pytest.raises(TokenError):
        decrypt_token(encrypt_token("t", new_key()), new_key())


def test_garbage():
    with pytest.raises(TokenError):
        decrypt_token(b"junk", new_key())


def test_keys_differ():
    assert new_key() != new_key()
