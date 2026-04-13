from __future__ import annotations

import json
import sqlite3


def log_operation(
    conn: sqlite3.Connection,
    operation: str,
    secret_name: str | None = None,
    details: dict | None = None,
) -> None:
    conn.execute(
        "INSERT INTO audit_log (operation, secret_name, details) VALUES (?, ?, ?)",
        (operation, secret_name, json.dumps(details or {})),
    )
    conn.commit()


def query_log(
    conn: sqlite3.Connection,
    secret_name: str | None = None,
    last_n: int = 50,
) -> list[dict]:
    if secret_name:
        rows = conn.execute(
            "SELECT id, timestamp, operation, secret_name, details "
            "FROM audit_log WHERE secret_name = ? "
            "ORDER BY id DESC LIMIT ?",
            (secret_name, last_n),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, timestamp, operation, secret_name, details "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            (last_n,),
        ).fetchall()
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "operation": r[2],
            "secret_name": r[3],
            "details": json.loads(r[4]) if r[4] else {},
        }
        for r in rows
    ]
