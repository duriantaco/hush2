from __future__ import annotations

import click


@click.command("history")
@click.argument("name")
@click.pass_context
def history_cmd(ctx, name):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR

    vault, console = _open_vault(ctx)
    try:
        history = vault.get_history(name)
        if not history:
            console.info(f"No history for '{name}'.")
            return

        if ctx.obj.get("json"):
            console.print_json(history)
        else:
            rows = []
            for entry in history:
                if entry["tags"]:
                    tags_str = ", ".join(entry["tags"])
                else:
                    tags_str = ""
                rows.append([
                    str(entry["version"]),
                    tags_str,
                    entry["archived_at"] or "",
                ])
            console.print_table(
                ["Version", "Tags", "Archived At"],
                rows,
                title=f"History: {name}",
            )
    finally:
        vault.close()
