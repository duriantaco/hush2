from click.testing import CliRunner

from hush2.cli import cli


def _init(runner):
    return runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})


def _invoke(runner, args):
    return runner.invoke(cli, args, env={"HUSH2_PASSWORD": "test123"})


class TestGenerate:
    def test_password(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = _invoke(runner, ["generate", "--type", "password", "-l", "16"])
            assert result.exit_code == 0
            assert len(result.output.strip()) == 16

    def test_token_hex(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = _invoke(runner, ["generate", "--type", "token", "-l", "8"])
            assert result.exit_code == 0
            # 8 bytes = 16 hex
            assert len(result.output.strip()) == 16 

    def test_key(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = _invoke(runner, ["generate", "--type", "key"])
            assert result.exit_code == 0
            assert len(result.output.strip()) > 0

    def test_uuid(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = _invoke(runner, ["generate", "--type", "uuid"])
            assert result.exit_code == 0
            # UUID format
            assert "-" in result.output 

    def test_save(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(runner, ["generate", "--type", "token", "--save", "MY_TOKEN"])
            assert result.exit_code == 0
            assert "saved" in result.output
            result = _invoke(runner, ["get", "MY_TOKEN"])
            assert result.exit_code == 0
            assert len(result.output.strip()) > 0
