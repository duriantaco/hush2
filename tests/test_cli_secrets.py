from click.testing import CliRunner

from hush2.cli import cli
from hush2.utils.exit_codes import AUTH_FAILED


def _init(runner, **kwargs):
    return runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"}, **kwargs)


def _invoke(runner, args, **kwargs):
    return runner.invoke(cli, args, env={"HUSH2_PASSWORD": "test123"}, **kwargs)


class TestSetGet:
    def test_set_and_get(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "API_KEY", "sk-123"])
            result = _invoke(runner, ["get", "API_KEY"])
            assert result.exit_code == 0
            assert "sk-123" in result.output

    def test_set_invalid_name(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(runner, ["set", "lowercase", "val"])
            assert result.exit_code != 0
            assert "Invalid name" in result.output

    def test_get_missing(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(runner, ["get", "NOPE"])
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_set_update(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "v1"])
            _invoke(runner, ["set", "KEY", "v2"])
            result = _invoke(runner, ["get", "KEY"])
            assert "v2" in result.output

    def test_wrong_password_is_rejected_before_write(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "correct-pass"})
            runner.invoke(
                cli, ["set", "API_KEY", "original"], env={"HUSH2_PASSWORD": "correct-pass"}
            )

            result = runner.invoke(
                cli, ["set", "NEW_KEY", "new-value"], env={"HUSH2_PASSWORD": "wrong-pass"}
            )
            assert result.exit_code == AUTH_FAILED
            assert "Failed to unlock vault" in result.output

            result = runner.invoke(
                cli, ["get", "API_KEY"], env={"HUSH2_PASSWORD": "correct-pass"}
            )
            assert result.exit_code == 0
            assert "original" in result.output

            result = runner.invoke(
                cli, ["get", "NEW_KEY"], env={"HUSH2_PASSWORD": "correct-pass"}
            )
            assert result.exit_code != 0
            assert "not found" in result.output


class TestList:
    def test_list(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "A_KEY", "1"])
            _invoke(runner, ["set", "B_KEY", "2"])
            result = _invoke(runner, ["list"])
            assert "A_KEY" in result.output
            assert "B_KEY" in result.output

    def test_list_json(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "val"])
            result = _invoke(runner, ["--json", "list"])
            assert '"name": "KEY"' in result.output

    def test_list_empty(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(runner, ["list"])
            assert "No secrets" in result.output


class TestRm:
    def test_rm(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "val"])
            result = _invoke(runner, ["rm", "KEY"])
            assert "deleted" in result.output
            result = _invoke(runner, ["get", "KEY"])
            assert "not found" in result.output

    def test_rm_bulk(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "A", "1"])
            _invoke(runner, ["set", "B", "2"])
            result = _invoke(runner, ["rm", "A", "B"])
            assert "A deleted" in result.output
            assert "B deleted" in result.output

    def test_rm_missing(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(runner, ["rm", "NOPE"])
            assert "not found" in result.output
