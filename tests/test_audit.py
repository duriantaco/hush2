from hush2.vault.audit import log_operation, query_log


class TestAuditLog:
    def test_log_and_query(self, vault):
        log_operation(vault.conn, "test_op", "MY_SECRET", {"key": "value"})
        entries = query_log(vault.conn, last_n=10)
        test_entries = [e for e in entries if e["operation"] == "test_op"]
        assert len(test_entries) == 1
        assert test_entries[0]["secret_name"] == "MY_SECRET"
        assert test_entries[0]["details"] == {"key": "value"}

    def test_filter_by_secret(self, vault):
        log_operation(vault.conn, "get", "A")
        log_operation(vault.conn, "get", "B")
        entries = query_log(vault.conn, secret_name="A")
        assert all(e["secret_name"] == "A" for e in entries)

    def test_vault_operations_logged(self, vault):
        vault.set_secret("KEY", "val")
        vault.get_secret("KEY")
        vault.delete_secret("KEY")
        entries = query_log(vault.conn, secret_name="KEY")
        ops = [e["operation"] for e in entries]
        assert "set" in ops
        assert "get" in ops
        assert "rm" in ops
