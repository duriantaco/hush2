from __future__ import annotations

import click


@click.command("tag")
@click.argument("name")
@click.argument("tags", nargs=-1, required=True)
@click.pass_context
def tag_cmd(ctx, name, tags):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR

    vault, console = _open_vault(ctx)
    try:
        for tag in tags:
            if not vault.add_tag(name, tag):
                console.error(f"Secret '{name}' not found.")
                ctx.exit(USER_ERROR)
                return
        console.success(f"Tagged {name}: {', '.join(tags)}")
    finally:
        vault.close()


@click.command("untag")
@click.argument("name")
@click.argument("tags", nargs=-1, required=True)
@click.pass_context
def untag_cmd(ctx, name, tags):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR

    vault, console = _open_vault(ctx)
    try:
        secret_names = {secret["name"] for secret in vault.list_secrets()}
        if name not in secret_names:
            console.error(f"Secret '{name}' not found.")
            ctx.exit(USER_ERROR)
            return

        removed = []
        for tag in tags:
            if vault.remove_tag(name, tag):
                removed.append(tag)

        if removed:
            console.success(f"Untagged {name}: {', '.join(removed)}")
        else:
            console.warn(f"{name} did not have any of the requested tags.")
    finally:
        vault.close()
