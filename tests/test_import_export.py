from hush2.commands.import_ import _parse_env
from hush2.commands.export import _escape_value

import re

NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class TestParseEnv:
    def test_basic(self):
        data = _parse_env("KEY=value", NAME_RE)
        assert data == {"KEY": "value"}

    def test_quoted(self):
        data = _parse_env('KEY="hello world"', NAME_RE)
        assert data == {"KEY": "hello world"}

    def test_single_quoted(self):
        data = _parse_env("KEY='hello'", NAME_RE)
        assert data == {"KEY": "hello"}

    def test_comments(self):
        data = _parse_env("# comment\nKEY=val", NAME_RE)
        assert data == {"KEY": "val"}

    def test_blank_lines(self):
        data = _parse_env("\n\nKEY=val\n\n", NAME_RE)
        assert data == {"KEY": "val"}

    def test_invalid_names_skipped(self):
        data = _parse_env("good_key=1\nVALID_KEY=2", NAME_RE)
        assert data == {"VALID_KEY": "2"}

    def test_multiple(self):
        text = "A=1\nB=2\nC=3"
        data = _parse_env(text, NAME_RE)
        assert data == {"A": "1", "B": "2", "C": "3"}


class TestEscapeValue:
    def test_simple(self):
        assert _escape_value("hello") == "hello"

    def test_spaces(self):
        assert _escape_value("hello world") == '"hello world"'

    def test_quotes(self):
        result = _escape_value('say "hi"')
        assert '\\"' in result

    def test_newlines(self):
        result = _escape_value("line1\nline2")
        assert "\\n" in result

    def test_dollar(self):
        result = _escape_value("$HOME")
        assert "\\$" in result
