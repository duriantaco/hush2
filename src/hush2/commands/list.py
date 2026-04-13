from __future__ import annotations

import click


@click.command("list")
@click.argument("what", required=False, default=None)
@click.option("--tag", "-t", default=None, help="Filter by tag.")
@click.pass_context
def list_cmd(ctx, what, tag):
    if what == "envs":
        _list_envs(ctx)
        return

    from hush2.cli import _open_vault

    vault, console = _open_vault(ctx)
    try:
        secrets = vault.list_secrets(tag=tag)
        if not secrets:
            console.info("No secrets found.")
            return

        if ctx.obj.get("json"):
            console.print_json(secrets)
        else:
            rows = []
            for s in secrets:
                tags_str = ", ".join(s["tags"]) if s["tags"] else ""
                rows.append([s["name"], tags_str, s["updated_at"] or ""])
            console.print_table(["Name", "Tags", "Updated"], rows)
    finally:
        vault.close()


def _list_envs(ctx):
    from pathlib import Path
    from hush2.vault.vault import Vault, VAULT_DIR_NAME

    console = ctx.obj["console"]
    global_ = ctx.obj.get("global", False)

    if global_:
        base = Path.home() / VAULT_DIR_NAME
    else:
        vault_base = Vault._find_local_vault_dir()
        if vault_base is None:
            console.info("No vault found.")
            return
        base = vault_base

    envs = Vault.list_environments(base)
    if not envs:
        console.info("No environments found.")
        return

    if ctx.obj.get("json"):
        console.print_json(envs)
    else:
        for e in envs:
            console.success(f"  {e}")
