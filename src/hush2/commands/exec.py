from __future__ import annotations

import os
import subprocess
import sys

import click


@click.command("exec", hidden=True)
@click.pass_context
def exec_cmd(ctx):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR
    from hush2.utils.masking import create_masker
    from hush2.vault import audit as audit_mod

    obj = ctx.obj
    console = obj["console"]
    secret_names = obj.get("exec_secrets", [])
    exec_tags = obj.get("exec_tags", [])
    cmd = obj.get("exec_cmd", [])
    no_mask = obj.get("no_mask", False)
    mask_style = obj.get("mask_style", "full")
    allow_env_fallback = obj.get("allow_env_fallback", False)

    if not cmd:
        console.error("No command specified after --")
        ctx.exit(USER_ERROR)
        return

    vault, _ = _open_vault(ctx)
    try:
        secrets = {}
        missing_names = []
        env_fallback_names = []
        vault_secret_count = 0

        if secret_names:
            for name in secret_names:
                val = vault.get_secret(name)
                if val is not None:
                    secrets[name] = val
                    vault_secret_count += 1
                elif allow_env_fallback and name in os.environ:
                    secrets[name] = os.environ[name]
                    env_fallback_names.append(name)
                else:
                    missing_names.append(name)

        for tag in exec_tags:
            tagged = vault.get_secrets_by_tag(tag)
            vault_secret_count += len(tagged)
            secrets.update(tagged)

        if missing_names:
            suffix = ""
            if not allow_env_fallback and any(name in os.environ for name in missing_names):
                suffix = " Use --allow-env-fallback to opt into parent environment values."
            names_str = ", ".join(missing_names)
            console.error(f"Missing vault secrets: {names_str}.{suffix}")
            ctx.exit(USER_ERROR)
            return

        if not secrets and (secret_names or exec_tags):
            console.error("No matching secrets found.")
            ctx.exit(USER_ERROR)
            return

        audit_mod.log_operation(
            vault.conn,
            "exec",
            details={
                "cmd": list(cmd),
                "secret_count": len(secrets),
                "vault_secret_count": vault_secret_count,
                "env_fallback_count": len(env_fallback_names),
                "env_fallback_names": env_fallback_names,
                "requested_secret_names": list(secret_names),
                "requested_tags": list(exec_tags),
            },
        )
    finally:
        vault.close()

    child_env = {**os.environ, **secrets}
    child_env.pop("HUSH2_PASSWORD", None)

    from hush2.utils.env_expand import expand_env_vars
    expanded_cmd = []
    for arg in cmd:
        expanded_cmd.append(expand_env_vars(arg, child_env))

    if no_mask:
        masker = None
    else:
        masker = create_masker(secrets, mask_style)

    exit_code = _run_with_masking(expanded_cmd, child_env, masker, console)
    sys.exit(exit_code)


def _run_with_masking(cmd, env, masker, console):
    from hush2.utils.exit_codes import USER_ERROR

    if masker is None:
        try:
            result = subprocess.run(cmd, env=env)
            return result.returncode
        except FileNotFoundError:
            console.error(f"Failed to launch command '{cmd[0]}': command not found.")
            return USER_ERROR
        except OSError as exc:
            console.error(f"Failed to launch command '{cmd[0]}': {exc}")
            return USER_ERROR

    try:
        proc = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        console.error(f"Failed to launch command '{cmd[0]}': command not found.")
        return USER_ERROR
    except OSError as exc:
        console.error(f"Failed to launch command '{cmd[0]}': {exc}")
        return USER_ERROR

    import threading

    def pipe_and_mask(input_stream, output_stream):
        for line in input_stream:
            text = line.decode("utf-8", errors="replace")
            masked = masker(text)
            output_stream.write(masked)
            output_stream.flush()

    t_out = threading.Thread(target=pipe_and_mask, args=(proc.stdout, sys.stdout))
    t_err = threading.Thread(target=pipe_and_mask, args=(proc.stderr, sys.stderr))
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    proc.wait()
    return proc.returncode
