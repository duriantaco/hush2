from pathlib import Path

from click.testing import CliRunner

from hush2.cli import cli


def _init(runner):
    return runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})


def _invoke(runner, args):
    return runner.invoke(cli, args, env={"HUSH2_PASSWORD": "test123"})


class TestScan:
    def test_clean_scan(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "supersecretvalue123"])
            Path("safe.txt").write_text("nothing secret here\n")
            result = _invoke(runner, ["scan", "--path", "."])
            assert "Clean" in result.output or result.exit_code == 0

    def test_finds_leaked_secret(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "TOKEN", "sk-live-very-secret-key"])
            Path("leaked.py").write_text('token = "sk-live-very-secret-key"\n')
            result = _invoke(runner, ["scan", "--path", "."])
            assert result.exit_code != 0
            assert "TOKEN" in result.output
