from pathlib import Path

from click.testing import CliRunner

from hush2.cli import cli


class TestInit:
    def test_init_creates_vault(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})
            assert result.exit_code == 0
            assert "Vault initialized" in result.output
            assert (Path(".hush2") / "envs" / "default" / "vault.db").exists()

    def test_init_with_env(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "--env", "staging"],
                env={"HUSH2_PASSWORD": "test123"},
            )
            assert result.exit_code == 0
            assert "staging" in result.output
            assert (Path(".hush2") / "envs" / "staging" / "vault.db").exists()

    def test_init_already_exists(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})
            result = runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})
            assert result.exit_code != 0
            assert "already exists" in result.output
