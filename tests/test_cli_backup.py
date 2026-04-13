from pathlib import Path

from click.testing import CliRunner

from hush2.cli import cli


def _init(runner):
    return runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})


def _invoke(runner, args):
    return runner.invoke(cli, args, env={"HUSH2_PASSWORD": "test123"})


class TestBackup:
    def test_backup_creates_file(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "value"])
            backup_file = str(tmp_path / "test.bak")
            result = _invoke(runner, ["backup", backup_file])
            assert result.exit_code == 0
            assert Path(backup_file).exists()


class TestRestore:
    def test_restore_round_trip(self, tmp_path):
        runner = CliRunner()
        backup_file = str(tmp_path / "test.bak")
        (tmp_path / "original").mkdir()
        (tmp_path / "restored").mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path / "original"):
            _init(runner)
            _invoke(runner, ["set", "SECRET", "mysecretvalue"])
            result = _invoke(runner, ["backup", backup_file])
            assert result.exit_code == 0

        with runner.isolated_filesystem(temp_dir=tmp_path / "restored"):
            result = _invoke(runner, ["restore", backup_file])
            assert result.exit_code == 0
            assert "restored" in result.output
            result = _invoke(runner, ["get", "SECRET"])
            assert result.exit_code == 0
            assert "mysecretvalue" in result.output

    def test_restore_recovers_keychain_password(self, tmp_path, monkeypatch):
        runner = CliRunner()
        backup_file = str(tmp_path / "test_keychain.bak")
        (tmp_path / "original").mkdir()
        (tmp_path / "restored").mkdir()

        keychain_store = {}

        def fake_store_password(vault_id, password):
            keychain_store[vault_id] = password
            return True

        def fake_get_keyring_password(vault_id):
            return keychain_store.get(vault_id)

        monkeypatch.setattr(
            "hush2.vault.keychain.store_password", fake_store_password
        )
        monkeypatch.setattr(
            "hush2.vault.keychain.get_keyring_password", fake_get_keyring_password
        )

        with runner.isolated_filesystem(temp_dir=tmp_path / "original"):
            result = runner.invoke(cli, ["init"], env={"HUSH2_PASSWORD": "test123"})
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["set", "SECRET", "restored-secret"], env={"HUSH2_PASSWORD": "test123"}
            )
            assert result.exit_code == 0
            result = runner.invoke(cli, ["backup", backup_file], env={"HUSH2_PASSWORD": "test123"})
            assert result.exit_code == 0

        with runner.isolated_filesystem(temp_dir=tmp_path / "restored"):
            result = runner.invoke(cli, ["restore", backup_file], env={})
            assert result.exit_code == 0
            result = runner.invoke(cli, ["get", "SECRET"], env={})
            assert result.exit_code == 0
            assert "restored-secret" in result.output
