from pathlib import Path

from click.testing import CliRunner

from hush2.cli import cli
from hush2.vault.crypto import derive_key
from hush2.vault.vault import Vault


def _invoke(runner, args, password="test123"):
    env = {"HUSH2_PASSWORD": password} if password is not None else {}
    return runner.invoke(cli, args, env=env)


def _corrupt_existing_secret(password="test123", wrong_password="wrongpass"):
    vault_dir = Path(".hush2") / "envs" / "default"
    salt = (vault_dir / "salt").read_bytes()

    correct_key = derive_key(password, salt)
    vault = Vault(vault_dir, correct_key)
    vault.open()
    vault.conn.execute("DELETE FROM vault_meta WHERE name = 'key_verifier'")
    vault.conn.commit()
    vault.close()

    wrong_key = derive_key(wrong_password, salt)
    wrong_vault = Vault(vault_dir, wrong_key)
    wrong_vault.open()
    wrong_vault.set_secret("KEY", "corrupted")
    wrong_vault.close()


def _create_ambiguous_legacy_vault(wrong_password="wrongpass"):
    vault_dir = Path(".hush2") / "envs" / "default"
    salt = (vault_dir / "salt").read_bytes()
    wrong_key = derive_key(wrong_password, salt)
    vault = Vault(vault_dir, wrong_key)
    vault.open()
    vault.conn.execute("DELETE FROM vault_meta WHERE name = 'key_verifier'")
    vault.conn.commit()
    vault.set_secret("BROKEN", "value")
    vault.close()


class TestDoctor:
    def test_doctor_repairs_corrupted_secret_from_history(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            assert _invoke(runner, ["init"]).exit_code == 0
            assert _invoke(runner, ["set", "KEY", "original"]).exit_code == 0
            _corrupt_existing_secret()

            result = _invoke(runner, ["doctor"])
            assert result.exit_code != 0
            assert "can be repaired" in result.output

            result = _invoke(runner, ["doctor", "--repair"])
            assert result.exit_code == 0
            assert "Repair complete" in result.output

            result = _invoke(runner, ["get", "KEY"])
            assert result.exit_code == 0
            assert "original" in result.output

    def test_doctor_force_repairs_ambiguous_legacy_vault(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            assert _invoke(runner, ["init"]).exit_code == 0
            _create_ambiguous_legacy_vault()

            result = _invoke(runner, ["doctor", "--repair"])
            assert result.exit_code != 0
            assert "--force" in result.output

            result = _invoke(runner, ["doctor", "--repair", "--force"])
            assert result.exit_code == 0
            assert "Removed unreadable current secrets" in result.output

            result = _invoke(runner, ["get", "BROKEN"])
            assert result.exit_code != 0
            assert "not found" in result.output
