"""Local SQLite storage for cheque records, settings, and an audit trail."""

from __future__ import annotations

import csv
from contextlib import contextmanager
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MeezanChequePrinter"
DEFAULT_DB_PATH = APP_DATA / "cheques.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or DEFAULT_DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def connection(self):
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cheques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    cheque_date TEXT NOT NULL,
                    payee TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    amount_words TEXT NOT NULL,
                    memo TEXT NOT NULL DEFAULT '',
                    internal_remarks TEXT NOT NULL DEFAULT '',
                    print_status TEXT NOT NULL DEFAULT 'Draft'
                        CHECK (print_status IN ('Draft', 'Submitted', 'Uncertain'))
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cheque_id INTEGER NOT NULL REFERENCES cheques(id),
                    changed_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cheques_date ON cheques(cheque_date);
                CREATE INDEX IF NOT EXISTS idx_cheques_payee ON cheques(payee);
                """
            )

    @staticmethod
    def _audit(connection: sqlite3.Connection, cheque_id: int, action: str) -> None:
        connection.execute(
            "INSERT INTO audit_log (cheque_id, changed_at, action) VALUES (?, ?, ?)",
            (cheque_id, utc_now(), action),
        )

    def save_draft(
        self,
        cheque_date: str,
        payee: str,
        amount: str,
        amount_words: str,
        memo: str = "",
        internal_remarks: str = "",
        cheque_id: int | None = None,
    ) -> int:
        now = utc_now()
        with self.connection() as connection:
            if cheque_id is not None:
                row = connection.execute(
                    "SELECT print_status FROM cheques WHERE id = ?", (cheque_id,)
                ).fetchone()
                if row is None:
                    raise ValueError("The selected cheque record no longer exists.")
                if row["print_status"] != "Draft":
                    raise ValueError("Submitted or uncertain cheque records cannot be edited.")
                connection.execute(
                    """UPDATE cheques SET modified_at=?, cheque_date=?, payee=?, amount=?,
                       amount_words=?, memo=?, internal_remarks=? WHERE id=?""",
                    (now, cheque_date, payee, amount, amount_words, memo, internal_remarks, cheque_id),
                )
                self._audit(connection, cheque_id, "Draft updated")
                return cheque_id
            cursor = connection.execute(
                """INSERT INTO cheques
                   (created_at, modified_at, cheque_date, payee, amount, amount_words, memo,
                    internal_remarks, print_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Draft')""",
                (now, now, cheque_date, payee, amount, amount_words, memo, internal_remarks),
            )
            record_id = int(cursor.lastrowid)
            self._audit(connection, record_id, "Draft created")
            return record_id

    def set_print_status(self, cheque_id: int, status: str) -> None:
        if status not in {"Submitted", "Uncertain"}:
            raise ValueError("Only Submitted or Uncertain are valid print status updates.")
        with self.connection() as connection:
            row = connection.execute(
                "SELECT print_status FROM cheques WHERE id = ?", (cheque_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Cheque record not found.")
            if row["print_status"] != "Draft":
                raise ValueError("This cheque already has a non-draft print status.")
            connection.execute(
                "UPDATE cheques SET print_status=?, modified_at=? WHERE id=?",
                (status, utc_now(), cheque_id),
            )
            self._audit(connection, cheque_id, f"Print status set to {status}")

    def get_cheque(self, cheque_id: int) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM cheques WHERE id=?", (cheque_id,)).fetchone()
            return dict(row) if row else None

    def search_cheques(
        self,
        query: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[str] = []
        if query.strip():
            pattern = f"%{query.strip()}%"
            clauses.append("(payee LIKE ? OR cheque_date LIKE ? OR amount LIKE ? OR memo LIKE ?)")
            parameters.extend((pattern, pattern, pattern, pattern))
        if date_from:
            clauses.append("cheque_date >= ?")
            parameters.append(date_from)
        if date_to:
            clauses.append("cheque_date <= ?")
            parameters.append(date_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connection() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    f"SELECT * FROM cheques {where} ORDER BY modified_at DESC, id DESC",
                    parameters,
                )
            ]

    def duplicate_as_draft(self, cheque_id: int) -> int:
        row = self.get_cheque(cheque_id)
        if row is None:
            raise ValueError("Cheque record not found.")
        return self.save_draft(
            row["cheque_date"], row["payee"], row["amount"], row["amount_words"],
            row["memo"], row["internal_remarks"],
        )

    def export_csv(self, cheque_ids: list[int], destination: Path) -> None:
        if not cheque_ids:
            raise ValueError("Select at least one record to export.")
        placeholders = ",".join("?" for _ in cheque_ids)
        with self.connection() as connection:
            rows = connection.execute(
                f"""SELECT id, created_at, modified_at, cheque_date, payee, amount,
                    amount_words, memo, internal_remarks, print_status
                    FROM cheques WHERE id IN ({placeholders}) ORDER BY id""",
                cheque_ids,
            ).fetchall()
        with Path(destination).open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(rows[0].keys() if rows else [
                "id", "created_at", "modified_at", "cheque_date", "payee", "amount",
                "amount_words", "memo", "internal_remarks", "print_status",
            ])
            writer.writerows([tuple(row) for row in rows])

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connection() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def backup_to(self, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
                target.commit()
            finally:
                target.close()

    def restore_from(self, source_path: Path) -> None:
        source_path = Path(source_path)
        if not source_path.is_file():
            raise ValueError("Backup file does not exist.")
        source = sqlite3.connect(source_path)
        try:
            integrity = source.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("The selected database backup failed its integrity check.")
            tables = {
                row[0] for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if not {"cheques", "settings"}.issubset(tables):
                raise ValueError("The selected file is not a Meezan Cheque Printer database.")
        finally:
            source.close()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.backup_to(self.path.with_name(f"{self.path.stem}.before-restore-{stamp}.sqlite3"))
        temporary = self.path.with_suffix(".restore.tmp")
        shutil.copy2(source_path, temporary)
        os.replace(temporary, self.path)
