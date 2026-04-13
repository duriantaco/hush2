import re

from hush2.utils.generators import (
    generate_key,
    generate_password,
    generate_token,
    generate_uuid,
)


class TestGeneratePassword:
    def test_default_length(self):
        pw = generate_password()
        assert len(pw) == 32

    def test_custom_length(self):
        pw = generate_password(length=16)
        assert len(pw) == 16

    def test_has_variety(self):
        pw = generate_password(length=32)
        assert any(c.isupper() for c in pw)
        assert any(c.islower() for c in pw)
        assert any(c.isdigit() for c in pw)

    def test_unique(self):
        a = generate_password()
        b = generate_password()
        assert a != b


class TestGenerateToken:
    def test_hex(self):
        t = generate_token(16, "hex")
        assert len(t) == 32
        assert all(c in "0123456789abcdef" for c in t)

    def test_base64(self):
        t = generate_token(16, "base64")
        assert len(t) > 0
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in t)


class TestGenerateKey:
    def test_key_is_base64(self):
        k = generate_key()
        import base64
        decoded = base64.b64decode(k)
        assert len(decoded) == 32


class TestGenerateUUID:
    def test_format(self):
        u = generate_uuid()
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            u,
        )
