from __future__ import annotations

import os
from pathlib import Path

from hush2.vault.crypto import derive_key, generate_salt

SERVICE_NAME = "hush2"
SALT_FILE = "salt"


def get_keyring_password(vault_id: str) -> str | None:
    try:
        import keyring
        return keyring.get_password(SERVICE_NAME, vault_id)
    except Exception:
        return None


def get_password(vault_id: str) -> str | None:
    """Retrieve the master password from keychain or env."""
    env_pw = os.environ.get("HUSH2_PASSWORD")
    if env_pw:
        return env_pw
    return get_keyring_password(vault_id)


def store_password(vault_id: str, password: str) -> bool:
    """Store the master password in the OS keychain. Returns True on success."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, vault_id, password)
        return True
    except Exception:
        return False


def delete_password(vault_id: str) -> bool:
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, vault_id)
        return True
    except Exception:
        return False


def get_or_create_salt(vault_dir: Path) -> bytes:
    """Read salt from vault dir, or create and persist a new one."""
    salt_path = vault_dir / SALT_FILE
    if salt_path.exists():
        return salt_path.read_bytes()
    salt = generate_salt()
    salt_path.write_bytes(salt)
    return salt


def unlock_key(vault_dir: Path, password: str) -> bytes:
    salt = get_or_create_salt(vault_dir)
    return derive_key(password, salt)
