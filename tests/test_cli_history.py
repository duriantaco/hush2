from click.testing import CliRunner

from hush2.cli import cli


def _init(runner):
    return runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})


def _invoke(runner, args):
    return runner.invoke(cli, args, env={"HUSH2_PASSWORD": "test123"})


class TestHistory:
    def test_history_shows_versions(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "v1"])
            _invoke(runner, ["set", "KEY", "v2"])
            _invoke(runner, ["set", "KEY", "v3"])
            result = _invoke(runner, ["history", "KEY"])
            assert result.exit_code == 0
            assert "1" in result.output
            assert "2" in result.output

    def test_history_empty(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "v1"])
            result = _invoke(runner, ["history", "KEY"])
            assert "No history" in result.output


class TestRollback:
    def test_rollback(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "original"])
            _invoke(runner, ["set", "KEY", "changed"])
            result = _invoke(runner, ["rollback", "KEY", "--to", "1"])
            assert result.exit_code == 0
            assert "rolled back" in result.output
            result = _invoke(runner, ["get", "KEY"])
            assert "original" in result.output

    def test_rollback_bad_version(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "v1"])
            result = _invoke(runner, ["rollback", "KEY", "--to", "99"])
            assert result.exit_code != 0
