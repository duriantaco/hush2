from __future__ import annotations

import click


@click.command("generate")
@click.option("--type", "-T", "gen_type", default="password",
              type=click.Choice(["password", "token", "key", "uuid"]),
              help="Type of secret to generate.")
@click.option("--length", "-l", default=32, type=int, help="Length (for password/token).")
@click.option("--encoding", default="hex", type=click.Choice(["hex", "base64"]),
              help="Encoding for token type.")
@click.option("--save", "save_as", default=None, help="Save to vault with this name.")
@click.option("--tag", "-t", "tags", multiple=True, help="Tags to apply (with --save).")
@click.pass_context
def generate_cmd(ctx, gen_type, length, encoding, save_as, tags):
    from hush2.utils.generators import (
        generate_password, generate_token, generate_key, generate_uuid,
    )
    import re

    console = ctx.obj["console"]

    if gen_type == "password":
        value = generate_password(length)
    elif gen_type == "token":
        value = generate_token(length, encoding)
    elif gen_type == "key":
        value = generate_key()
    elif gen_type == "uuid":
        value = generate_uuid()
    else:
        value = generate_password(length)

    if save_as:
        if not re.match(r"^[A-Z][A-Z0-9_]*$", save_as):
            console.error(
                f"Invalid name '{save_as}'. Must be uppercase letters, digits, and underscores."
            )
            ctx.exit(2)
            return

        from hush2.cli import _open_vault
        vault, _ = _open_vault(ctx)
        try:
            vault.set_secret(save_as, value, list(tags) if tags else None)
            console.success(f"Generated {gen_type} saved as {save_as}")
        finally:
            vault.close()
    else:
        if ctx.obj.get("json"):
            console.print_json({"type": gen_type, "value": value})
        else:
            console.print_value(value)
