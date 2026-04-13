from __future__ import annotations

import click


@click.command("rm")
@click.argument("names", nargs=-1, required=True)
@click.pass_context
def rm_cmd(ctx, names):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR

    vault, console = _open_vault(ctx)
    try:
        deleted = []
        missing = []
        for name in names:
            if vault.delete_secret(name):
                deleted.append(name)
            else:
                missing.append(name)

        for name in deleted:
            console.success(f"{name} deleted")
        for name in missing:
            console.warn(f"'{name}' not found")

        if not deleted:
            ctx.exit(USER_ERROR)
    finally:
        vault.close()
