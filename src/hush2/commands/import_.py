from __future__ import annotations

import os
import re

import click


@click.command("import")
@click.argument("file", required=False, default=None)
@click.option("--stdin", "from_stdin", is_flag=True, help="Read from stdin.")
@click.option("--from-env", is_flag=True, help="Import from current environment variables.")
@click.option("--pattern", default=None, help="Regex filter for --from-env variable names.")
@click.option("--tag", "-t", "tags", multiple=True, help="Tags to apply to imported secrets.")
@click.pass_context
def import_cmd(ctx, file, from_stdin, from_env, pattern, tags):
    from hush2.cli import _open_vault
    from hush2.utils.input import read_stdin
    from hush2.utils.exit_codes import USER_ERROR

    console = ctx.obj["console"]
    name_re = re.compile(r"^[A-Z][A-Z0-9_]*$")

    if from_env:
        data = {}
        if pattern:
            pat = re.compile(pattern)
        else:
            pat = None
        for key, val in os.environ.items():
            if not name_re.match(key):
                continue
            if pat and not pat.search(key):
                continue
            data[key] = val
    elif from_stdin:
        raw = read_stdin()
        if not raw:
            console.error("No data received from stdin.")
            ctx.exit(USER_ERROR)
            return
        data = _parse_env(raw, name_re)
    elif file:
        try:
            with open(file) as f:
                raw = f.read()
        except FileNotFoundError:
            console.error(f"File not found: {file}")
            ctx.exit(USER_ERROR)
            return
        data = _parse_env(raw, name_re)
    else:
        console.error("Specify a file, --stdin, or --from-env.")
        ctx.exit(USER_ERROR)
        return

    if not data:
        console.warn("No valid secrets found to import.")
        return

    vault, _ = _open_vault(ctx)
    try:
        count = vault.import_secrets(data, list(tags) if tags else None)
        console.success(f"Imported {count} secret{'s' if count != 1 else ''}")
    finally:
        vault.close()


def _parse_env(text: str, name_re: re.Pattern) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]

        if name_re.match(key):
            result[key] = value
    return result
