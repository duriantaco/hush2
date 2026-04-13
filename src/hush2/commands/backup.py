from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import click

from hush2 import __version__


BACKUP_MAGIC = b"HUSH2BACKUP\n"


@click.command("backup")
@click.argument("file", required=False, default=None)
@click.pass_context
def backup_cmd(ctx, file):
    from hush2.cli import _open_vault

    vault, console = _open_vault(ctx)
    vault.close()

    db_path = vault.db_path
    salt_path = vault.vault_dir / "salt"

    if not db_path.exists():
        console.error("Vault database not found.")
        ctx.exit(1)
        return

    if file is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file = f"hush2_backup_{timestamp}.bak"

    salt_b64 = ""
    if salt_path.exists():
        salt_b64 = base64.b64encode(salt_path.read_bytes()).decode()

    metadata = {
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vault_path": str(vault.vault_dir),
        "salt": salt_b64,
    }
    meta_bytes = json.dumps(metadata).encode()

    with open(file, "wb") as f:
        f.write(BACKUP_MAGIC)
        f.write(meta_bytes)
        f.write(b"\n")
        f.write(db_path.read_bytes())

    console.success(f"Backup created: {file}")


@click.command("restore")
@click.argument("file")
@click.option("--env", default=None, help="Restore into a specific environment.")
@click.pass_context
def restore_cmd(ctx, file, env):
    from hush2.vault.vault import VAULT_DIR_NAME
    from hush2.vault.keychain import get_keyring_password, store_password
    from hush2.utils.exit_codes import USER_ERROR

    console = ctx.obj["console"]
    global_ = ctx.obj.get("global", False)

    backup_path = Path(file)
    if not backup_path.exists():
        console.error(f"Backup file not found: {file}")
        ctx.exit(USER_ERROR)
        return

    raw = backup_path.read_bytes()
    if not raw.startswith(BACKUP_MAGIC):
        console.error("Invalid backup file (missing header).")
        ctx.exit(USER_ERROR)
        return

    try:
        rest = raw[len(BACKUP_MAGIC):]
        newline_idx = rest.index(b"\n")
        meta_json = rest[:newline_idx]
        db_bytes = rest[newline_idx + 1:]
        metadata = json.loads(meta_json)
    except (ValueError, json.JSONDecodeError):
        console.error("Invalid backup file (corrupt metadata).")
        ctx.exit(USER_ERROR)
        return

    console.info(f"Backup from {metadata.get('timestamp', 'unknown')}, "
                 f"hush2 v{metadata.get('version', '?')}")

    if global_:
        base = Path.home() / VAULT_DIR_NAME
    else:
        base = Path.cwd() / VAULT_DIR_NAME

    if env:
        vault_dir = base / "envs" / env
    else:
        vault_dir = base / "envs" / "default"

    vault_dir.mkdir(parents=True, exist_ok=True)
    db_path = vault_dir / "vault.db"

    if db_path.exists():
        console.warn("Existing vault will be overwritten.")

    db_path.write_bytes(db_bytes)

    salt_b64 = metadata.get("salt", "")
    if salt_b64:
        salt_path = vault_dir / "salt"
        salt_path.write_bytes(base64.b64decode(salt_b64))

    restored_password = None
    source_vault_id = metadata.get("vault_path")
    if isinstance(source_vault_id, str) and source_vault_id:
        restored_password = get_keyring_password(source_vault_id)
    if restored_password is None:
        restored_password = os.environ.get("HUSH2_PASSWORD")

    if restored_password:
        if not store_password(str(vault_dir), restored_password):
            console.warn(
                "Vault restored, but the password could not be stored in the OS keychain. "
                "Use HUSH2_PASSWORD to unlock this vault."
            )
    else:
        console.warn(
            "Vault restored, but no password could be recovered. "
            "Set HUSH2_PASSWORD to the original vault password when opening it."
        )

    console.success(f"Vault restored to {vault_dir}")
