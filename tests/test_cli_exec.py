"""CLI integration tests for exec-pattern secret injection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner

from hush2.cli import cli
from hush2.utils.exit_codes import USER_ERROR


def _init(runner, env=None):
    command_env = {"HUSH2_PASSWORD": "test123"}
    if env:
        command_env.update(env)
    return runner.invoke(cli, ["init"], env=command_env)


def _invoke(runner, args, env=None):
    command_env = {"HUSH2_PASSWORD": "test123"}
    if env:
        command_env.update(env)
    return runner.invoke(cli, args, env=command_env)


class TestExecPattern:
    def test_run_subcommand_with_separator_is_not_hijacked_by_exec_dispatch(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            _invoke(runner, ["set", "KEY", "vault-value"])
            result = _invoke(
                runner,
                ["run", "--no-mask", "--", "echo", "$KEY"],
            )

            assert result.exit_code == 0
            assert "Missing vault secrets: run" not in result.output

    def test_exec_requires_requested_secret_to_exist_in_vault_by_default(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(
                runner,
                ["MISSING_SECRET", "--", "echo", "$MISSING_SECRET"],
                env={"MISSING_SECRET": "parent-env-value"},
            )

            assert result.exit_code == USER_ERROR
            assert "Missing vault secrets: MISSING_SECRET." in result.output
            assert "--allow-env-fallback" in result.output

    def test_exec_can_explicitly_fallback_to_parent_environment(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(
                runner,
                [
                    "--allow-env-fallback",
                    "MISSING_SECRET",
                    "--",
                    sys.executable,
                    "-c",
                    "from pathlib import Path; import os; Path('proof.txt').write_text(os.environ['MISSING_SECRET'])",
                ],
                env={"MISSING_SECRET": "parent-env-value"},
            )

            assert result.exit_code == 0
            assert Path("proof.txt").read_text() == "parent-env-value"

    def test_exec_audit_records_env_fallback_usage(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _init(runner)
            result = _invoke(
                runner,
                [
                    "--allow-env-fallback",
                    "--no-mask",
                    "MISSING_SECRET",
                    "--",
                    "echo",
                    "$MISSING_SECRET",
                ],
                env={"MISSING_SECRET": "parent-env-value"},
            )
            assert result.exit_code == 0

            audit_result = _invoke(runner, ["--json", "audit", "--last", "10"])
            assert audit_result.exit_code == 0
            entries = json.loads(audit_result.output)
            exec_entries = [entry for entry in entries if entry["operation"] == "exec"]
            assert exec_entries
            latest = exec_entries[0]["details"]
            assert latest["env_fallback_count"] == 1
            assert latest["env_fallback_names"] == ["MISSING_SECRET"]
