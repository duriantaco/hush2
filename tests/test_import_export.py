import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from hush2.cli import cli
from hush2.commands.export import _escape_value
from hush2.commands.import_ import _parse_env

NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _init(runner, env=None):
    command_env = {"HUSH2_PASSWORD": "test123"}
    if env:
        command_env.update(env)
    return runner.invoke(cli, ["init"], env=command_env)


def _invoke(runner, args, env=None):
    command_env = {"HUSH2_PASSWORD": "test123"}
    if env:
        command_env.update(env)
    return runner.invoke(cli, args, env=command_env)


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

    @pytest.mark.parametrize(
        "value",
        [
            "line1\nline2",
            "path\\to\\file",
            'say "hi"',
            "$HOME",
            "`date`",
            "  padded value  ",
        ],
    )
    def test_exported_values_round_trip(self, value):
        text = f"KEY={_escape_value(value)}"
        data = _parse_env(text, NAME_RE)
        assert data == {"KEY": value}


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


class TestImportExportCLI:
    def test_cli_round_trip_for_escaped_value(self, tmp_path):
        runner = CliRunner()
        value = 'line1\npath\\to\\file "$HOME" `date`'

        with runner.isolated_filesystem(temp_dir=tmp_path):
            assert _init(runner).exit_code == 0
            Path("input.env").write_text(f"KEY={_escape_value(value)}\n")

            result = _invoke(runner, ["import", "input.env"])
            assert result.exit_code == 0

            result = _invoke(runner, ["export", "--env-file", "output.env"])
            assert result.exit_code == 0
            assert _parse_env(Path("output.env").read_text(), NAME_RE) == {"KEY": value}

    def test_cli_import_from_env_honors_pattern(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            assert _init(runner).exit_code == 0
            result = _invoke(
                runner,
                ["import", "--from-env", "--pattern", "^KEEP_"],
                env={"KEEP_TOKEN": "value-1", "DROP_TOKEN": "value-2"},
            )
            assert result.exit_code == 0

            result = _invoke(runner, ["get", "KEEP_TOKEN"])
            assert result.exit_code == 0
            assert "value-1" in result.output

            result = _invoke(runner, ["get", "DROP_TOKEN"])
            assert result.exit_code != 0

    def test_cli_import_requires_a_source(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            assert _init(runner).exit_code == 0
            result = _invoke(runner, ["import"])
            assert result.exit_code != 0
            assert "Specify a file, --stdin, or --from-env." in result.output

    def test_cli_export_json_output(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            assert _init(runner).exit_code == 0
            assert _invoke(runner, ["set", "API_KEY", "abc123"]).exit_code == 0

            result = _invoke(runner, ["--json", "export"])
            assert result.exit_code == 0
            assert '"API_KEY": "abc123"' in result.output
