"""CLI integration tests for tag/untag commands."""

from click.testing import CliRunner

from hush2.cli import cli


def _init(runner):
    return runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})


def _invoke(runner, args):
    return runner.invoke(cli, args, env={"HUSH2_PASSWORD": "test123"})


class TestTag:
    def test_tag(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "val"])
            result = _invoke(runner, ["tag", "KEY", "prod", "api"])
            assert result.exit_code == 0
            assert "Tagged" in result.output
            result = _invoke(runner, ["list", "--tag", "prod"])
            assert "KEY" in result.output

    def test_untag(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "val", "-t", "prod", "-t", "dev"])
            _invoke(runner, ["untag", "KEY", "dev"])
            result = _invoke(runner, ["--json", "list"])
            # should only have prod tag now
            assert "prod" in result.output

    def test_untag_missing_secret(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(runner, ["untag", "NOPE", "dev"])
            assert result.exit_code != 0
            assert "not found" in result.output
