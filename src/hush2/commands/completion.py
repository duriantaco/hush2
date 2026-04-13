from __future__ import annotations

import click


@click.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion_cmd(shell):
    import os

    if shell == "bash":
        os.environ["_HUSH2_COMPLETE"] = "bash_source"
    elif shell == "zsh":
        os.environ["_HUSH2_COMPLETE"] = "zsh_source"
    elif shell == "fish":
        os.environ["_HUSH2_COMPLETE"] = "fish_source"

    from hush2.cli import cli
    try:
        cli(standalone_mode=False)
    except SystemExit:
        pass
