"""Scoped query functions — each agent only calls its own function."""
import sqlite3
from config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_company_data(account_id: str) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM company_registry WHERE account_id = ?", (account_id,)
        ).fetchone()
    return dict(row) if row else {}


def get_adverse_media(account_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM adverse_media WHERE account_id = ? ORDER BY published_date DESC",
            (account_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_payment_history(account_id: str) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM payment_history WHERE account_id = ?", (account_id,)
        ).fetchone()
    return dict(row) if row else {}


def get_sanctions_data(name: str, account_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sanctions_pep WHERE account_id = ? OR name LIKE ?",
            (account_id, f"%{name}%"),
        ).fetchall()
    return [dict(r) for r in rows]
