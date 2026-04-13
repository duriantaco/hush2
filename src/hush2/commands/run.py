from __future__ import annotations

import os
import subprocess
import sys
import threading

import click


@click.command("run", context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
    allow_interspersed_args=False,
))
@click.option("--tag", "-t", "tags", multiple=True, help="Only inject secrets with this tag.")
@click.option("--no-mask", is_flag=True, help="Disable output masking.")
@click.option("--mask-style", default="full", type=click.Choice(["full", "partial", "hash"]),
              help="Masking style (default: full).")
@click.argument("cmd", nargs=-1, type=click.UNPROCESSED, required=True)
@click.pass_context
def run_cmd(ctx, tags, no_mask, mask_style, cmd):
    from hush2.cli import _open_vault
    from hush2.utils.masking import create_masker
    from hush2.vault import audit as audit_mod

    vault, console = _open_vault(ctx)
    try:
        if tags:
            secrets = {}
            for tag in tags:
                secrets.update(vault.get_secrets_by_tag(tag))
        else:
            secrets = vault.get_all_secrets()

        if not secrets:
            console.warn("No secrets to inject.")

        audit_mod.log_operation(
            vault.conn, "run",
            details={"cmd": list(cmd), "secret_count": len(secrets)},
        )
    finally:
        vault.close()

    child_env = {**os.environ, **secrets}
    child_env.pop("HUSH2_PASSWORD", None)

    if no_mask:
        masker = None
    else:
        masker = create_masker(secrets, mask_style)

    if masker is None:
        result = subprocess.run(list(cmd), env=child_env)
        sys.exit(result.returncode)

    proc = subprocess.Popen(
        list(cmd), env=child_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    def pipe_and_mask(input_stream, output_stream):
        for line in input_stream:
            text = line.decode("utf-8", errors="replace")
            output_stream.write(masker(text))
            output_stream.flush()

    t_out = threading.Thread(target=pipe_and_mask, args=(proc.stdout, sys.stdout))
    t_err = threading.Thread(target=pipe_and_mask, args=(proc.stderr, sys.stderr))
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    proc.wait()
    sys.exit(proc.returncode)
