import pytest

from hush2.vault.crypto import derive_key
from hush2.vault.vault import Vault


class TestSecretCRUD:
    def test_set_and_get(self, vault):
        vault.set_secret("API_KEY", "sk-123")
        assert vault.get_secret("API_KEY") == "sk-123"

    def test_get_missing(self, vault):
        assert vault.get_secret("NOPE") is None

    def test_update(self, vault):
        vault.set_secret("KEY", "v1")
        vault.set_secret("KEY", "v2")
        assert vault.get_secret("KEY") == "v2"

    def test_delete(self, vault):
        vault.set_secret("KEY", "val")
        assert vault.delete_secret("KEY") is True
        assert vault.get_secret("KEY") is None

    def test_delete_missing(self, vault):
        assert vault.delete_secret("NOPE") is False

    def test_list(self, vault):
        vault.set_secret("A_KEY", "1")
        vault.set_secret("B_KEY", "2")
        names = [s["name"] for s in vault.list_secrets()]
        assert names == ["A_KEY", "B_KEY"]

    def test_get_secrets_batch(self, vault):
        vault.set_secret("X", "1")
        vault.set_secret("Y", "2")
        result = vault.get_secrets(["X", "Y", "Z"])
        assert result == {"X": "1", "Y": "2"}

    def test_get_all(self, vault):
        vault.set_secret("A", "1")
        vault.set_secret("B", "2")
        assert vault.get_all_secrets() == {"A": "1", "B": "2"}


class TestTags:
    def test_set_with_tags(self, vault):
        vault.set_secret("KEY", "val", tags=["prod", "api"])
        assert vault.get_tags("KEY") == ["prod", "api"]

    def test_add_tag(self, vault):
        vault.set_secret("KEY", "val")
        vault.add_tag("KEY", "prod")
        assert vault.get_tags("KEY") == ["prod"]

    def test_remove_tag(self, vault):
        vault.set_secret("KEY", "val", tags=["prod", "db"])
        vault.remove_tag("KEY", "prod")
        assert vault.get_tags("KEY") == ["db"]

    def test_list_by_tag(self, vault):
        vault.set_secret("A", "1", tags=["web"])
        vault.set_secret("B", "2", tags=["db"])
        vault.set_secret("C", "3", tags=["web", "db"])
        web = [s["name"] for s in vault.list_secrets(tag="web")]
        assert web == ["A", "C"]

    def test_get_by_tag(self, vault):
        vault.set_secret("A", "1", tags=["prod"])
        vault.set_secret("B", "2", tags=["dev"])
        result = vault.get_secrets_by_tag("prod")
        assert result == {"A": "1"}


class TestHistory:
    def test_history_created_on_update(self, vault):
        vault.set_secret("KEY", "v1")
        vault.set_secret("KEY", "v2")
        vault.set_secret("KEY", "v3")
        history = vault.get_history("KEY")
        assert len(history) == 2
        assert history[0]["version"] == 2
        assert history[1]["version"] == 1

    def test_history_value(self, vault):
        vault.set_secret("KEY", "original")
        vault.set_secret("KEY", "updated")
        val = vault.get_history_value("KEY", 1)
        assert val == "original"

    def test_rollback(self, vault):
        vault.set_secret("KEY", "v1")
        vault.set_secret("KEY", "v2")
        assert vault.rollback("KEY", 1) is True
        assert vault.get_secret("KEY") == "v1"

    def test_rollback_is_reversible(self, vault):
        vault.set_secret("KEY", "v1")
        vault.set_secret("KEY", "v2")
        vault.rollback("KEY", 1)
        history = vault.get_history("KEY")
        versions = [h["version"] for h in history]
        assert 2 in versions

    def test_rollback_missing_version(self, vault):
        vault.set_secret("KEY", "v1")
        assert vault.rollback("KEY", 99) is False

    def test_history_pruned(self, vault):
        for i in range(15):
            vault.set_secret("KEY", f"v{i}")
        history = vault.get_history("KEY")
        assert len(history) <= 10


class TestImportExport:
    def test_import_and_export(self, vault):
        data = {"X_KEY": "val1", "Y_KEY": "val2"}
        count = vault.import_secrets(data)
        assert count == 2
        exported = vault.export_all()
        assert exported == data

    def test_import_with_tags(self, vault):
        vault.import_secrets({"KEY": "val"}, tags=["imported"])
        assert vault.get_tags("KEY") == ["imported"]


class TestAuthentication:
    def test_validate_access_bootstraps_verifier(self, vault_dir, vault_key, vault_salt):
        (vault_dir / "salt").write_bytes(vault_salt)
        vault = Vault(vault_dir, vault_key)
        vault.open()
        assert vault.validate_access() == "ok"

        verifier = vault.conn.execute(
            "SELECT name FROM vault_meta WHERE name = 'key_verifier'"
        ).fetchone()
        vault.close()

        assert verifier is not None

    def test_validate_access_rejects_wrong_key(self, vault_dir, vault_salt):
        (vault_dir / "salt").write_bytes(vault_salt)

        correct_key = derive_key("correct-password", vault_salt)
        vault = Vault(vault_dir, correct_key)
        vault.open()
        vault.initialize_key_verifier()
        vault.set_secret("API_KEY", "sk-123")
        vault.close()

        wrong_key = derive_key("wrong-password", vault_salt)
        wrong_vault = Vault(vault_dir, wrong_key)
        wrong_vault.open()
        status = wrong_vault.validate_access()
        wrong_vault.close()

        assert status == "bad_key"

    def test_inspect_health_marks_legacy_vault_without_verifier(self, vault_dir, vault_key, vault_salt):
        (vault_dir / "salt").write_bytes(vault_salt)
        vault = Vault(vault_dir, vault_key)
        vault.open()
        vault.set_secret("API_KEY", "sk-123")
        health = vault.inspect_health()
        vault.close()

        assert health["status"] == "legacy_unverified"
        assert health["current"]["decryptable"] == ["API_KEY"]

    def test_repair_restores_corrupted_current_from_history(self, vault_dir, vault_salt):
        (vault_dir / "salt").write_bytes(vault_salt)

        correct_key = derive_key("correct-password", vault_salt)
        vault = Vault(vault_dir, correct_key)
        vault.open()
        vault.initialize_key_verifier()
        vault.set_secret("API_KEY", "original")
        vault.conn.execute("DELETE FROM vault_meta WHERE name = 'key_verifier'")
        vault.conn.commit()
        vault.close()

        wrong_key = derive_key("wrong-password", vault_salt)
        wrong_vault = Vault(vault_dir, wrong_key)
        wrong_vault.open()
        wrong_vault.set_secret("API_KEY", "corrupted")
        wrong_vault.close()

        repaired_vault = Vault(vault_dir, correct_key)
        repaired_vault.open()
        result = repaired_vault.repair()
        value = repaired_vault.get_secret("API_KEY")
        health = repaired_vault.inspect_health()
        repaired_vault.close()

        assert result["restored_current"] == [{"name": "API_KEY", "from_version": 1}]
        assert value == "original"
        assert health["status"] == "ok"

    def test_repair_force_cleans_ambiguous_legacy_vault(self, vault_dir, vault_salt):
        (vault_dir / "salt").write_bytes(vault_salt)

        wrong_key = derive_key("wrong-password", vault_salt)
        wrong_vault = Vault(vault_dir, wrong_key)
        wrong_vault.open()
        wrong_vault.set_secret("BROKEN", "value")
        wrong_vault.close()

        correct_key = derive_key("correct-password", vault_salt)
        vault = Vault(vault_dir, correct_key)
        vault.open()
        assert vault.inspect_health()["status"] == "ambiguous"

        with pytest.raises(ValueError, match="ambiguous"):
            vault.repair()

        result = vault.repair(force=True)
        health = vault.inspect_health()
        vault.close()

        assert result["removed_current"] == ["BROKEN"]
        assert result["initialized_verifier"] is True
        assert health["status"] == "ok"
