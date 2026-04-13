from __future__ import annotations

from pathlib import Path

import click


@click.command("init")
@click.option("--global", "-g", "global_", is_flag=True, help="Create global vault in ~/.hush2.")
@click.option("--env", default=None, help="Environment name (default: 'default').")
@click.pass_context
def init_cmd(ctx, global_, env):
    from hush2.vault.vault import Vault, VAULT_DIR_NAME
    from hush2.vault.keychain import get_or_create_salt, store_password
    from hush2.vault.crypto import derive_key
    from hush2.utils.input import read_password
    from hush2.utils.exit_codes import USER_ERROR

    obj = ctx.obj
    console = obj["console"]
    global_ = global_ or obj.get("global", False)
    env = env or obj.get("env")

    if global_:
        base = Path.home() / VAULT_DIR_NAME
    else:
        base = Path.cwd() / VAULT_DIR_NAME

    if env:
        vault_dir = base / "envs" / env
    else:
        vault_dir = base / "envs" / "default"

    if (vault_dir / "vault.db").exists():
        console.error(f"Vault already exists at {vault_dir}")
        ctx.exit(USER_ERROR)
        return

    vault_dir.mkdir(parents=True, exist_ok=True)

    import os
    password = os.environ.get("HUSH2_PASSWORD")
    if not password:
        password = read_password("Enter vault password: ")
        confirm = read_password("Confirm password: ")
        if password != confirm:
            console.error("Passwords do not match.")
            ctx.exit(USER_ERROR)
            return

    salt = get_or_create_salt(vault_dir)
    key = derive_key(password, salt)

    vault_id = str(vault_dir)
    password_stored = store_password(vault_id, password)

    vault = Vault(vault_dir, key)
    vault.open()
    vault.initialize_key_verifier()
    vault.close()

    env_label = env or "default"
    location = "global" if global_ else "local"
    console.success(f"Vault initialized ({location}, env: {env_label})")
    console.info(f"  {vault_dir}")
    if not password_stored:
        console.warn(
            "Could not store the vault password in the OS keychain. "
            "Use HUSH2_PASSWORD to unlock this vault."
        )
