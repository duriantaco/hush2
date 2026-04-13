from __future__ import annotations

import click


@click.command("audit")
@click.option("--secret", "-s", default=None, help="Filter by secret name.")
@click.option("--last", "-n", "last_n", default=50, type=int, help="Number of entries (default 50).")
@click.pass_context
def audit_cmd(ctx, secret, last_n):
    from hush2.cli import _open_vault
    from hush2.vault.audit import query_log

    vault, console = _open_vault(ctx)
    try:
        entries = query_log(vault.conn, secret_name=secret, last_n=last_n)

        if not entries:
            console.info("No audit log entries.")
            return

        if ctx.obj.get("json"):
            console.print_json(entries)
        else:
            rows = []
            for e in entries:
                details_str = ""
                if e["details"]:
                    details_str = ", ".join(f"{k}={v}" for k, v in e["details"].items())
                rows.append([
                    str(e["id"]),
                    e["timestamp"] or "",
                    e["operation"],
                    e["secret_name"] or "-",
                    details_str,
                ])
            console.print_table(
                ["ID", "Timestamp", "Operation", "Secret", "Details"],
                rows,
                title="Audit Log",
            )
    finally:
        vault.close()
