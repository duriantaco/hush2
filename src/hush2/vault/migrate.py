"""Database schema creation and migration."""

from __future__ import annotations

import sqlite3

CURRENT_VERSION = 2

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS secrets (
    name TEXT PRIMARY KEY,
    encrypted_value BLOB NOT NULL,
    iv BLOB NOT NULL,
    tags TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS secrets_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    encrypted_value BLOB NOT NULL,
    iv BLOB NOT NULL,
    tags TEXT DEFAULT '[]',
    archived_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_history_name ON secrets_history(name);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    operation TEXT NOT NULL,
    secret_name TEXT,
    details TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS vault_meta (
    name TEXT PRIMARY KEY,
    encrypted_value BLOB NOT NULL,
    iv BLOB NOT NULL,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create or migrate tables, then update the schema version."""
    conn.executescript(SCHEMA_V1)
    conn.executescript(SCHEMA_V2)
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (CURRENT_VERSION,)
        )
    elif row[0] < CURRENT_VERSION:
        conn.execute(
            "UPDATE schema_version SET version = ?", (CURRENT_VERSION,)
        )
    conn.commit()
