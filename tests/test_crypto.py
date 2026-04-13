import pytest

from hush2.vault.crypto import decrypt, derive_key, encrypt, generate_salt


class TestEncryptDecrypt:
    def test_round_trip(self):
        salt = generate_salt()
        key = derive_key("password", salt)
        ct, iv = encrypt("hello world", key)
        assert decrypt(ct, iv, key) == "hello world"

    def test_empty_string(self):
        salt = generate_salt()
        key = derive_key("pw", salt)
        ct, iv = encrypt("", key)
        assert decrypt(ct, iv, key) == ""

    def test_unicode(self):
        salt = generate_salt()
        key = derive_key("pw", salt)
        text = "secrets with unicode: cafe\u0301 \U0001f512"
        ct, iv = encrypt(text, key)
        assert decrypt(ct, iv, key) == text

    def test_wrong_key_fails(self):
        salt = generate_salt()
        key1 = derive_key("password1", salt)
        key2 = derive_key("password2", salt)
        ct, iv = encrypt("secret", key1)
        with pytest.raises(Exception):
            decrypt(ct, iv, key2)

    def test_unique_ivs(self):
        salt = generate_salt()
        key = derive_key("pw", salt)
        _, iv1 = encrypt("same", key)
        _, iv2 = encrypt("same", key)
        assert iv1 != iv2


class TestKeyDerivation:
    def test_deterministic(self):
        salt = generate_salt()
        k1 = derive_key("password", salt)
        k2 = derive_key("password", salt)
        assert k1 == k2

    def test_different_salts(self):
        s1 = generate_salt()
        s2 = generate_salt()
        k1 = derive_key("password", s1)
        k2 = derive_key("password", s2)
        assert k1 != k2

    def test_different_passwords(self):
        salt = generate_salt()
        k1 = derive_key("password1", salt)
        k2 = derive_key("password2", salt)
        assert k1 != k2

    def test_key_length(self):
        salt = generate_salt()
        key = derive_key("pw", salt)
        assert len(key) == 32


class TestGenerateSalt:
    def test_length(self):
        assert len(generate_salt()) == 16

    def test_unique(self):
        assert generate_salt() != generate_salt()
