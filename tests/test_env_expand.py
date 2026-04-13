from hush2.utils.env_expand import expand_env_vars


class TestEnvExpand:
    def test_dollar_var(self):
        assert expand_env_vars("$HOME/bin", {"HOME": "/usr"}) == "/usr/bin"

    def test_braced_var(self):
        assert expand_env_vars("${HOME}/bin", {"HOME": "/usr"}) == "/usr/bin"

    def test_missing_var_empty(self):
        assert expand_env_vars("$MISSING", {}) == ""

    def test_no_vars(self):
        assert expand_env_vars("plain text", {"X": "1"}) == "plain text"

    def test_multiple_vars(self):
        env = {"A": "1", "B": "2"}
        assert expand_env_vars("$A-$B", env) == "1-2"

    def test_no_shell_injection(self):
        result = expand_env_vars("$(whoami)", {"whoami": "nope"})
        # should NOT execute shell commands
        assert "root" not in result
