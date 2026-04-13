from __future__ import annotations

import re

import click


@click.command("set")
@click.argument("name")
@click.argument("value", required=False, default=None)
@click.option("--stdin", "from_stdin", is_flag=True, help="Read value from stdin.")
@click.option("--tag", "-t", "tags", multiple=True, help="Tags to apply.")
@click.pass_context
def set_cmd(ctx, name, value, from_stdin, tags):
    from hush2.utils.input import read_secret_value, read_stdin
    from hush2.utils.exit_codes import USER_ERROR

    console = ctx.obj["console"]

    if not re.match(r"^[A-Z][A-Z0-9_]*$", name):
        console.error(
            f"Invalid name '{name}'. Must be uppercase letters, digits, and underscores "
            "(e.g. API_KEY, DB_URL)."
        )
        ctx.exit(USER_ERROR)
        return

    if from_stdin:
        value = read_stdin().strip()
        if not value:
            console.error("No value received from stdin.")
            ctx.exit(USER_ERROR)
            return
    elif value is None:
        value = read_secret_value(f"Enter value for {name}: ")
        if not value:
            console.error("Empty value.")
            ctx.exit(USER_ERROR)
            return

    from hush2.cli import _open_vault

    vault, _ = _open_vault(ctx)
    try:
        existing = vault.get_secret(name) is not None
        vault.set_secret(name, value, list(tags) if tags else None)
        action = "updated" if existing else "set"
        console.success(f"{name} {action}")
    finally:
        vault.close()
