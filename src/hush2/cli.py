"""CLI entry point — click group with -- dispatch for exec pattern."""

from __future__ import annotations

import sys

import click

from hush2.utils.output import HushConsole, OutputMode


class HushGroup(click.Group):
    """Custom group that intercepts the -- exec pattern before normal routing."""

    @staticmethod
    def _consumes_value(arg: str) -> bool:
        return arg in ("--tag", "-t", "--env", "--mask-style")

    def _is_exec_pattern(self, before: list[str]) -> bool:
        """Return True only for bare exec-pattern invocations.

        Examples intercepted:
            hush2 API_KEY -- cmd
            hush2 --tag prod -- cmd

        Examples left alone:
            hush2 run --tag prod -- cmd
            hush2 list --json
        """
        i = 0
        while i < len(before):
            arg = before[i]
            if self._consumes_value(arg) and i + 1 < len(before):
                i += 2
                continue
            if arg.startswith("-"):
                i += 1
                continue
            return arg not in self.commands
        return True

    def parse_args(self, ctx, args):
        if "--" in args:
            idx = args.index("--")
            before = args[:idx]
            after = args[idx + 1:]
            if not self._is_exec_pattern(before):
                return super().parse_args(ctx, args)
            ctx.ensure_object(dict)
            ctx.obj["exec_secrets"] = []
            ctx.obj["exec_tags"] = []
            ctx.obj["exec_cmd"] = after

            remaining = []
            i = 0
            while i < len(before):
                arg = before[i]
                if arg in ("--tag", "-t") and i + 1 < len(before):
                    ctx.obj["exec_tags"].append(before[i + 1])
                    i += 2
                elif arg in ("--json",):
                    ctx.obj.setdefault("json", True)
                    i += 1
                elif arg in ("--quiet", "-q"):
                    ctx.obj.setdefault("quiet", True)
                    i += 1
                elif arg in ("--global", "-g"):
                    ctx.obj.setdefault("global", True)
                    i += 1
                elif arg in ("--env",) and i + 1 < len(before):
                    ctx.obj["env"] = before[i + 1]
                    i += 2
                elif arg in ("--no-mask",):
                    ctx.obj["no_mask"] = True
                    i += 1
                elif arg in ("--allow-env-fallback",):
                    ctx.obj["allow_env_fallback"] = True
                    i += 1
                elif arg in ("--mask-style",) and i + 1 < len(before):
                    ctx.obj["mask_style"] = before[i + 1]
                    i += 2
                elif not arg.startswith("-"):
                    ctx.obj["exec_secrets"].append(arg)
                    i += 1
                else:
                    remaining.append(arg)
                    i += 1

            args = ["exec"] + remaining
        return super().parse_args(ctx, args)


def _get_console(ctx: click.Context) -> HushConsole:
    """Build a HushConsole from context flags."""
    obj = ctx.ensure_object(dict)
    if obj.get("json"):
        mode = OutputMode.JSON
    elif obj.get("quiet"):
        mode = OutputMode.QUIET
    else:
        mode = OutputMode.HUMAN
    return HushConsole(mode)


def _resolve_vault_access(ctx: click.Context):
    """Resolve the current vault path, password, and console."""
    from hush2.vault.vault import Vault
    from hush2.vault.keychain import get_password
    from hush2.utils.exit_codes import AUTH_FAILED, NO_VAULT

    obj = ctx.obj
    console = obj["console"]
    global_ = obj.get("global", False)
    env = obj.get("env")

    vault_path = Vault.find_vault_path(global_=global_, env=env)
    if vault_path is None:
        console.error("No vault found. Run 'hush2 init' first.")
        ctx.exit(NO_VAULT)
        raise SystemExit(NO_VAULT)

    vault_id = str(vault_path)
    password = get_password(vault_id)
    if password is None:
        console.error(
            "Could not retrieve vault password. "
            "Set HUSH2_PASSWORD env var or re-init the vault."
        )
        ctx.exit(AUTH_FAILED)
        raise SystemExit(AUTH_FAILED)

    return vault_path, password, console


def _open_vault_raw(ctx: click.Context):
    from hush2.vault.vault import Vault
    from hush2.vault.keychain import unlock_key

    vault_path, password, console = _resolve_vault_access(ctx)
    key = unlock_key(vault_path, password)
    vault = Vault(vault_path, key)
    vault.open()
    return vault, console


@click.group(cls=HushGroup)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output.")
@click.option("--global", "-g", "global_", is_flag=True, help="Use global vault (~/.hush2).")
@click.option("--env", default=None, help="Environment name.")
@click.pass_context
def cli(ctx, use_json, quiet, global_, env):
    """hush2 — local encrypted secrets manager for developer and agent workflows."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = ctx.obj.get("json") or use_json
    ctx.obj["quiet"] = ctx.obj.get("quiet") or quiet
    ctx.obj["global"] = ctx.obj.get("global") or global_
    if env:
        ctx.obj["env"] = env
    ctx.obj["console"] = _get_console(ctx)


def _open_vault(ctx: click.Context):
    """Find and open the vault, returning (vault, console). Exits on failure."""
    from hush2.utils.exit_codes import AUTH_FAILED, ERROR
    vault, console = _open_vault_raw(ctx)

    access_status = vault.validate_access()
    if access_status != "ok":
        vault.close()
        if access_status == "corrupted":
            console.error(
                "Vault data is corrupted and some secrets cannot be decrypted."
            )
            ctx.exit(ERROR)
            raise SystemExit(ERROR)

        console.error(
            "Failed to unlock vault. Check HUSH2_PASSWORD or the stored keychain password."
        )
        ctx.exit(AUTH_FAILED)
        raise SystemExit(AUTH_FAILED)

    return vault, console


from hush2.commands.init import init_cmd
from hush2.commands.set import set_cmd
from hush2.commands.get import get_cmd
from hush2.commands.list import list_cmd
from hush2.commands.rm import rm_cmd
from hush2.commands.exec import exec_cmd
from hush2.commands.run import run_cmd
from hush2.commands.import_ import import_cmd
from hush2.commands.export import export_cmd
from hush2.commands.tag import tag_cmd, untag_cmd
from hush2.commands.history import history_cmd
from hush2.commands.rollback import rollback_cmd
from hush2.commands.generate import generate_cmd
from hush2.commands.audit import audit_cmd
from hush2.commands.scan import scan_cmd
from hush2.commands.backup import backup_cmd, restore_cmd
from hush2.commands.completion import completion_cmd
from hush2.commands.doctor import doctor_cmd

cli.add_command(init_cmd, "init")
cli.add_command(set_cmd, "set")
cli.add_command(get_cmd, "get")
cli.add_command(list_cmd, "list")
cli.add_command(rm_cmd, "rm")
cli.add_command(exec_cmd, "exec")
cli.add_command(run_cmd, "run")
cli.add_command(import_cmd, "import")
cli.add_command(export_cmd, "export")
cli.add_command(tag_cmd, "tag")
cli.add_command(untag_cmd, "untag")
cli.add_command(history_cmd, "history")
cli.add_command(rollback_cmd, "rollback")
cli.add_command(generate_cmd, "generate")
cli.add_command(audit_cmd, "audit")
cli.add_command(scan_cmd, "scan")
cli.add_command(backup_cmd, "backup")
cli.add_command(restore_cmd, "restore")
cli.add_command(completion_cmd, "completion")
cli.add_command(doctor_cmd, "doctor")
