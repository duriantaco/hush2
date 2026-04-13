from __future__ import annotations

import click


@click.command("rollback")
@click.argument("name")
@click.option("--to", "version", required=True, type=int, help="Version number to restore.")
@click.pass_context
def rollback_cmd(ctx, name, version):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR

    vault, console = _open_vault(ctx)
    try:
        if vault.rollback(name, version):
            console.success(f"{name} rolled back to version {version}")
        else:
            console.error(f"Version {version} not found for '{name}'.")
            ctx.exit(USER_ERROR)
    finally:
        vault.close()
