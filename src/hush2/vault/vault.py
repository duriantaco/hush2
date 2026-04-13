from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from hush2.vault import audit as audit_mod
from hush2.vault.crypto import decrypt, encrypt
from hush2.vault.migrate import ensure_schema

SECRET_NAME_PATTERN = r"^[A-Z][A-Z0-9_]*$"
MAX_HISTORY = 10
VAULT_DIR_NAME = ".hush2"
DB_NAME = "vault.db"
KEY_VERIFIER_NAME = "key_verifier"
KEY_VERIFIER_VALUE = "hush2-auth-verifier-v1"


class Vault:
    """Encrypted secrets vault backed by SQLite.

    Usage::

        with Vault(vault_dir, key) as v:
            v.set_secret("API_KEY", "sk-xxx")
            print(v.get_secret("API_KEY"))
    """

    def __init__(self, vault_dir: str | Path, key: bytes) -> None:
        self.vault_dir = Path(vault_dir)
        self.key = key
        self.db_path = self.vault_dir / DB_NAME
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> Vault:
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def open(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(self._conn)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Vault is not open")
        return self._conn

    def initialize_key_verifier(self) -> None:
        """Persist an encrypted verifier so future unlocks can be authenticated."""
        ciphertext, iv = encrypt(KEY_VERIFIER_VALUE, self.key)
        self.conn.execute(
            "INSERT INTO vault_meta (name, encrypted_value, iv, updated_at) "
            "VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now')) "
            "ON CONFLICT(name) DO UPDATE SET "
            "encrypted_value = excluded.encrypted_value, "
            "iv = excluded.iv, "
            "updated_at = excluded.updated_at",
            (KEY_VERIFIER_NAME, ciphertext, iv),
        )
        self.conn.commit()

    def inspect_health(self) -> dict:
        """Inspect whether the vault can be authenticated and fully decrypted."""
        report = {
            "status": "ok",
            "verifier_present": False,
            "verifier_valid": None,
            "current": {"decryptable": [], "corrupted": []},
            "history": {"decryptable": [], "corrupted": []},
        }

        verifier = self.conn.execute(
            "SELECT encrypted_value, iv FROM vault_meta WHERE name = ?",
            (KEY_VERIFIER_NAME,),
        ).fetchone()
        report["verifier_present"] = verifier is not None

        if verifier is not None:
            try:
                report["verifier_valid"] = (
                    decrypt(verifier[0], verifier[1], self.key) == KEY_VERIFIER_VALUE
                )
            except Exception:
                report["verifier_valid"] = False
            if not report["verifier_valid"]:
                report["status"] = "bad_key"
                return report

        for name, ciphertext, iv in self.conn.execute(
            "SELECT name, encrypted_value, iv FROM secrets ORDER BY name"
        ).fetchall():
            try:
                decrypt(ciphertext, iv, self.key)
                report["current"]["decryptable"].append(name)
            except Exception:
                report["current"]["corrupted"].append(name)

        for row_id, name, version, ciphertext, iv in self.conn.execute(
            "SELECT id, name, version, encrypted_value, iv "
            "FROM secrets_history ORDER BY name, version DESC"
        ).fetchall():
            entry = {"id": row_id, "name": name, "version": version}
            try:
                decrypt(ciphertext, iv, self.key)
                report["history"]["decryptable"].append(entry)
            except Exception:
                report["history"]["corrupted"].append(entry)

        corrupted_count = (
            len(report["current"]["corrupted"]) + len(report["history"]["corrupted"])
        )
        decryptable_count = (
            len(report["current"]["decryptable"]) + len(report["history"]["decryptable"])
        )

        if verifier is None:
            if corrupted_count and decryptable_count == 0:
                report["status"] = "ambiguous"
            elif corrupted_count:
                report["status"] = "corrupted"
            else:
                report["status"] = "legacy_unverified"
        elif corrupted_count:
            report["status"] = "corrupted"

        return report

    def validate_access(self) -> str:
        """Validate that the active key can authenticate and decrypt current data.

        Returns:
            "ok" for a usable vault
            "bad_key" for an invalid password/key
            "corrupted" when the key is valid but stored data is unreadable
        """
        health = self.inspect_health()
        if health["status"] in {"bad_key", "ambiguous"}:
            return "bad_key"
        if health["status"] == "corrupted":
            return "corrupted"
        if not health["verifier_present"]:
            self.initialize_key_verifier()

        return "ok"

    def repair(self, force: bool = False) -> dict:
        """Repair decryptable legacy corruption and anchor the current key."""
        before = self.inspect_health()
        status = before["status"]

        if status == "bad_key":
            raise ValueError("bad_key")
        if status == "ambiguous" and not force:
            raise ValueError("ambiguous")

        result = {
            "status_before": status,
            "status_after": status,
            "restored_current": [],
            "removed_current": [],
            "removed_history": [],
            "initialized_verifier": False,
            "forced": force,
        }

        if status in {"corrupted", "ambiguous"}:
            latest_history = {}
            corrupted_history = []

            for row_id, name, version, ciphertext, iv, tags_json in self.conn.execute(
                "SELECT id, name, version, encrypted_value, iv, tags "
                "FROM secrets_history ORDER BY name, version DESC"
            ).fetchall():
                try:
                    decrypt(ciphertext, iv, self.key)
                    latest_history.setdefault(
                        name,
                        {
                            "version": version,
                            "encrypted_value": ciphertext,
                            "iv": iv,
                            "tags": tags_json,
                        },
                    )
                except Exception:
                    corrupted_history.append(
                        {"id": row_id, "name": name, "version": version}
                    )

            deleted_secret_names: set[str] = set()
            for name, ciphertext, iv in self.conn.execute(
                "SELECT name, encrypted_value, iv FROM secrets ORDER BY name"
            ).fetchall():
                try:
                    decrypt(ciphertext, iv, self.key)
                except Exception:
                    replacement = latest_history.get(name)
                    if replacement is not None:
                        self.conn.execute(
                            "UPDATE secrets SET encrypted_value = ?, iv = ?, tags = ?, "
                            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE name = ?",
                            (
                                replacement["encrypted_value"],
                                replacement["iv"],
                                replacement["tags"],
                                name,
                            ),
                        )
                        result["restored_current"].append(
                            {"name": name, "from_version": replacement["version"]}
                        )
                    else:
                        deleted_secret_names.add(name)
                        self.conn.execute("DELETE FROM secrets WHERE name = ?", (name,))
                        self.conn.execute(
                            "DELETE FROM secrets_history WHERE name = ?", (name,)
                        )
                        result["removed_current"].append(name)

            for entry in corrupted_history:
                if entry["name"] in deleted_secret_names:
                    continue
                self.conn.execute(
                    "DELETE FROM secrets_history WHERE id = ?", (entry["id"],)
                )
                result["removed_history"].append(
                    {"name": entry["name"], "version": entry["version"]}
                )

            self.conn.commit()

        if not before["verifier_present"]:
            self.initialize_key_verifier()
            result["initialized_verifier"] = True

        after = self.inspect_health()
        result["status_after"] = after["status"]

        if after["status"] not in {"ok", "legacy_unverified"}:
            raise RuntimeError("repair_incomplete")

        audit_mod.log_operation(
            self.conn,
            "repair",
            details={
                "status_before": result["status_before"],
                "status_after": result["status_after"],
                "restored_current": len(result["restored_current"]),
                "removed_current": len(result["removed_current"]),
                "removed_history": len(result["removed_history"]),
                "initialized_verifier": result["initialized_verifier"],
                "forced": force,
            },
        )

        return result


    def set_secret(self, name: str, value: str, tags: list[str] | None = None) -> None:
        """Encrypt and store a secret. Archives the old version if it exists."""
        existing = self.conn.execute(
            "SELECT encrypted_value, iv, tags FROM secrets WHERE name = ?", (name,)
        ).fetchone()

        if existing:
            self._archive(name, existing)

        ciphertext, iv = encrypt(value, self.key)
        tags_json = json.dumps(tags or [])

        if existing:
            self.conn.execute(
                "UPDATE secrets SET encrypted_value = ?, iv = ?, tags = ?, "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE name = ?",
                (ciphertext, iv, tags_json, name),
            )
        else:
            self.conn.execute(
                "INSERT INTO secrets (name, encrypted_value, iv, tags) VALUES (?, ?, ?, ?)",
                (name, ciphertext, iv, tags_json),
            )
        self.conn.commit()
        self._prune_history(name)
        audit_mod.log_operation(self.conn, "set", name)

    def get_secret(self, name: str) -> str | None:
        """Decrypt and return a secret value, or None if not found."""
        row = self.conn.execute(
            "SELECT encrypted_value, iv FROM secrets WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        audit_mod.log_operation(self.conn, "get", name)
        return decrypt(row[0], row[1], self.key)

    def get_secrets(self, names: list[str]) -> dict[str, str]:
        result = {}
        for name in names:
            val = self.get_secret(name)
            if val is not None:
                result[name] = val
        return result

    def get_all_secrets(self) -> dict[str, str]:
        """Decrypt and return all secrets."""
        rows = self.conn.execute(
            "SELECT name, encrypted_value, iv FROM secrets"
        ).fetchall()
        result = {}
        for name, ct, iv in rows:
            result[name] = decrypt(ct, iv, self.key)
        if result:
            audit_mod.log_operation(self.conn, "get_all", details={"count": len(result)})
        return result

    def get_secrets_by_tag(self, tag: str) -> dict[str, str]:
        rows = self.conn.execute(
            "SELECT name, encrypted_value, iv, tags FROM secrets"
        ).fetchall()
        result = {}
        for name, ct, iv, tags_json in rows:
            tags = json.loads(tags_json) if tags_json else []
            if tag in tags:
                result[name] = decrypt(ct, iv, self.key)
        if result:
            audit_mod.log_operation(
                self.conn, "get_by_tag", details={"tag": tag, "count": len(result)}
            )
        return result

    def list_secrets(self, tag: str | None = None) -> list[dict]:
        rows = self.conn.execute(
            "SELECT name, tags, created_at, updated_at FROM secrets ORDER BY name"
        ).fetchall()
        results = []
        for name, tags_json, created, updated in rows:
            tags = json.loads(tags_json) if tags_json else []
            if tag and tag not in tags:
                continue
            results.append({
                "name": name,
                "tags": tags,
                "created_at": created,
                "updated_at": updated,
            })
        return results

    def delete_secret(self, name: str) -> bool:
        """Delete a secret and its history. Returns True if it existed."""
        row = self.conn.execute(
            "SELECT 1 FROM secrets WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return False
        self.conn.execute("DELETE FROM secrets WHERE name = ?", (name,))
        self.conn.execute("DELETE FROM secrets_history WHERE name = ?", (name,))
        self.conn.commit()
        audit_mod.log_operation(self.conn, "rm", name)
        return True


    def get_tags(self, name: str) -> list[str]:
        row = self.conn.execute(
            "SELECT tags FROM secrets WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return []
        return json.loads(row[0]) if row[0] else []

    def set_tags(self, name: str, tags: list[str]) -> bool:
        tags_json = json.dumps(tags)
        cur = self.conn.execute(
            "UPDATE secrets SET tags = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE name = ?",
            (tags_json, name),
        )
        self.conn.commit()
        if cur.rowcount > 0:
            audit_mod.log_operation(self.conn, "tag", name, {"tags": tags})
        return cur.rowcount > 0

    def add_tag(self, name: str, tag: str) -> bool:
        tags = self.get_tags(name)
        if tag in tags:
            return True
        tags.append(tag)
        return self.set_tags(name, tags)

    def remove_tag(self, name: str, tag: str) -> bool:
        tags = self.get_tags(name)
        if tag not in tags:
            return False
        tags.remove(tag)
        return self.set_tags(name, tags)


    def get_history(self, name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT version, tags, archived_at FROM secrets_history "
            "WHERE name = ? ORDER BY version DESC",
            (name,),
        ).fetchall()
        return [
            {"version": r[0], "tags": json.loads(r[1]) if r[1] else [], "archived_at": r[2]}
            for r in rows
        ]

    def get_history_value(self, name: str, version: int) -> str | None:
        """Decrypt a specific historical version."""
        row = self.conn.execute(
            "SELECT encrypted_value, iv FROM secrets_history "
            "WHERE name = ? AND version = ?",
            (name, version),
        ).fetchone()
        if row is None:
            return None
        return decrypt(row[0], row[1], self.key)

    def rollback(self, name: str, target_version: int) -> bool:
        hist_row = self.conn.execute(
            "SELECT encrypted_value, iv, tags FROM secrets_history "
            "WHERE name = ? AND version = ?",
            (name, target_version),
        ).fetchone()
        if hist_row is None:
            return False

        current = self.conn.execute(
            "SELECT encrypted_value, iv, tags FROM secrets WHERE name = ?", (name,)
        ).fetchone()
        if current:
            self._archive(name, current)

        self.conn.execute(
            "UPDATE secrets SET encrypted_value = ?, iv = ?, tags = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE name = ?",
            (hist_row[0], hist_row[1], hist_row[2], name),
        )
        self.conn.commit()
        self._prune_history(name)
        audit_mod.log_operation(
            self.conn, "rollback", name, {"to_version": target_version}
        )
        return True


    def export_all(self) -> dict[str, str]:
        return self.get_all_secrets()

    def import_secrets(self, data: dict[str, str], tags: list[str] | None = None) -> int:
        count = 0
        for name, value in data.items():
            self.set_secret(name, value, tags)
            count += 1
        if count:
            audit_mod.log_operation(
                self.conn, "import", details={"count": count}
            )
        return count


    def _archive(self, name: str, row: tuple) -> None:
        """Archive the current version to history."""
        encrypted_value, iv, tags_json = row
        last = self.conn.execute(
            "SELECT MAX(version) FROM secrets_history WHERE name = ?", (name,)
        ).fetchone()
        version = (last[0] or 0) + 1
        self.conn.execute(
            "INSERT INTO secrets_history (name, version, encrypted_value, iv, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, version, encrypted_value, iv, tags_json),
        )
        self.conn.commit()

    def _prune_history(self, name: str, keep: int = MAX_HISTORY) -> None:
        """Remove old history entries beyond the keep limit."""
        self.conn.execute(
            "DELETE FROM secrets_history WHERE name = ? AND id NOT IN "
            "(SELECT id FROM secrets_history WHERE name = ? ORDER BY version DESC LIMIT ?)",
            (name, name, keep),
        )
        self.conn.commit()


    @staticmethod
    def find_vault_path(global_: bool = False, env: str | None = None) -> Path | None:
        """Locate the vault directory.

        Search order:
        - Global: ~/.hush2/ or ~/.hush2/envs/<env>/
        - Local: walk up from cwd looking for .hush2/, then check envs/<env>/ within it
        """
        if global_:
            base = Path.home() / VAULT_DIR_NAME
        else:
            base = Vault._find_local_vault_dir()
            if base is None:
                return None

        if env:
            vault_dir = base / "envs" / env
        else:
            default_env = base / "envs" / "default"
            if default_env.exists():
                vault_dir = default_env
            elif (base / DB_NAME).exists():
                vault_dir = base
            else:
                vault_dir = default_env
        return vault_dir if vault_dir.exists() else None

    @staticmethod
    def _find_local_vault_dir() -> Path | None:
        current = Path.cwd()
        while True:
            candidate = current / VAULT_DIR_NAME
            if candidate.is_dir():
                return candidate
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    @staticmethod
    def init_vault(
        path: Path, password: str, global_: bool = False, env: str | None = None
    ) -> Path:
        from hush2.vault.keychain import get_or_create_salt, store_password

        if env:
            vault_dir = path / "envs" / env
        else:
            vault_dir = path / "envs" / "default"

        vault_dir.mkdir(parents=True, exist_ok=True)

        salt = get_or_create_salt(vault_dir)
        from hush2.vault.crypto import derive_key
        key = derive_key(password, salt)

        vault_id = str(vault_dir)
        store_password(vault_id, password)

        vault = Vault(vault_dir, key)
        vault.open()
        vault.initialize_key_verifier()
        vault.close()

        return vault_dir

    @staticmethod
    def list_environments(base_path: Path) -> list[str]:
        envs_dir = base_path / "envs"
        if not envs_dir.is_dir():
            return []
        return sorted(
            d.name for d in envs_dir.iterdir() if d.is_dir() and (d / DB_NAME).exists()
        )
