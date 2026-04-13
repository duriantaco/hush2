"""hush2 get — retrieve a secret value."""

from __future__ import annotations

import click


@click.command("get")
@click.argument("name")
@click.option("--clip", is_flag=True, help="Copy to clipboard (auto-clears after 30s).")
@click.pass_context
def get_cmd(ctx, name, clip):
    """Decrypt and display a secret."""
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR

    vault, console = _open_vault(ctx)
    try:
        value = vault.get_secret(name)
        if value is None:
            console.error(f"Secret '{name}' not found.")
            ctx.exit(USER_ERROR)
            return

        if clip:
            _copy_to_clipboard(value, console)
        else:
            console.print_value(value)
    finally:
        vault.close()


def _copy_to_clipboard(value: str, console):
    import subprocess
    import sys
    import threading

    if sys.platform == "darwin":
        cmd = ["pbcopy"]
    else:
        cmd = ["xclip", "-selection", "clipboard"]

    try:
        subprocess.run(cmd, input=value.encode(), check=True, capture_output=True)
        console.success("Copied to clipboard (auto-clears in 30s)")

        def clear():
            try:
                subprocess.run(cmd, input=b"", check=True, capture_output=True)
            except Exception:
                pass

        timer = threading.Timer(30.0, clear)
        timer.daemon = True
        timer.start()
    except FileNotFoundError:
        console.warn("Clipboard tool not found (pbcopy/xclip). Printing instead.")
        console.print_value(value)
