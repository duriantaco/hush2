from __future__ import annotations

import click


@click.command("export")
@click.option("--env-file", "-f", default=None, help="Write to file instead of stdout.")
@click.option("--tag", "-t", default=None, help="Only export secrets with this tag.")
@click.pass_context
def export_cmd(ctx, env_file, tag):
    from hush2.cli import _open_vault

    vault, console = _open_vault(ctx)
    try:
        if tag:
            secrets = vault.get_secrets_by_tag(tag)
        else:
            secrets = vault.export_all()

        if not secrets:
            console.warn("No secrets to export.")
            return

        lines = []
        for name in sorted(secrets):
            value = secrets[name]
            lines.append(f"{name}={_escape_value(value)}")

        output = "\n".join(lines) + "\n"

        if env_file:
            with open(env_file, "w") as f:
                f.write(output)
            console.success(f"Exported {len(secrets)} secret(s) to {env_file}")
        else:
            if ctx.obj.get("json"):
                console.print_json(secrets)
            else:
                click.echo(output, nl=False)

        from hush2.vault import audit as audit_mod
        audit_mod.log_operation(
            vault.conn, "export", details={"count": len(secrets)}
        )
    finally:
        vault.close()


def _escape_value(value: str) -> str:
    special_chars = (" ", '"', "'", "\n", "\\", "$", "`", "#")
    needs_quoting = False
    for c in special_chars:
        if c in value:
            needs_quoting = True
            break
    if not needs_quoting:
        return value
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("$", "\\$")
    escaped = escaped.replace("`", "\\`")
    return f'"{escaped}"'
