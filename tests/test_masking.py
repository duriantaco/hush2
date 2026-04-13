from hush2.utils.masking import create_masker


class TestMasking:
    def test_full_mode(self):
        masker = create_masker({"KEY": "secret123"}, "full")
        assert masker("my secret123 here") == "my [REDACTED] here"

    def test_partial_mode(self):
        masker = create_masker({"KEY": "secret123"}, "partial")
        assert masker("my secret123 here") == "my se...23 here"

    def test_hash_mode(self):
        masker = create_masker({"KEY": "secret123"}, "hash")
        result = masker("my secret123 here")
        assert result.startswith("my [sha:")
        assert result.endswith("] here")

    def test_empty_secrets(self):
        masker = create_masker({}, "full")
        assert masker("unchanged") == "unchanged"

    def test_multiple_secrets(self):
        masker = create_masker({"A": "aaa", "B": "bbb"}, "full")
        assert masker("aaa and bbb") == "[REDACTED] and [REDACTED]"

    def test_longer_secret_replaced_first(self):
        masker = create_masker({"SHORT": "abc", "LONG": "abcdef"}, "full")
        result = masker("abcdef")
        assert result == "[REDACTED]"

    def test_short_secret_full_mode(self):
        masker = create_masker({"K": "x"}, "full")
        assert masker("x") == "[REDACTED]"

    def test_partial_short_secret(self):
        masker = create_masker({"K": "ab"}, "partial")
        # too short for partial, falls back to REDACTED
        assert masker("ab") == "[REDACTED]"
