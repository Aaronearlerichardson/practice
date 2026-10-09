"""Task 02: idempotent, atomic reload of one site-quarter with an audit trail (sqlite3).

Implement the functions below. Keep the names and signatures; the tests import them.
The schema is given: don't change table or column names.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

EXPECTED_HEADER = ["patient_id", "test_code", "collected_date", "value", "unit"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lab_results (
    site_id        TEXT NOT NULL,
    quarter        TEXT NOT NULL,
    patient_id     TEXT NOT NULL,
    test_code      TEXT NOT NULL,
    collected_date TEXT NOT NULL,
    value          REAL NOT NULL,
    unit           TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS load_audit (
    load_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id    TEXT NOT NULL,
    quarter    TEXT NOT NULL,
    file_name  TEXT NOT NULL,
    checksum   TEXT NOT NULL,
    row_count  INTEGER NOT NULL,
    status     TEXT NOT NULL,
    message    TEXT NOT NULL DEFAULT '',
    loaded_at  TEXT NOT NULL
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Create lab_results and load_audit if they don't exist (safe to call twice)."""
    raise NotImplementedError


def file_checksum(path: str | Path) -> str:
    """SHA-256 hex digest of the file's raw bytes."""
    raise NotImplementedError


def parse_quarter(quarter: str) -> tuple[date, date]:
    """'2024Q1' -> (date(2024, 1, 1), date(2024, 4, 1)): start inclusive, end exclusive.

    Anything not matching YYYYQ[1-4] raises ValueError.
    """
    raise NotImplementedError


def read_and_validate(path: str | Path, quarter: str) -> list[tuple[str, str, str, float, str]]:
    """Parse and validate the whole file before anything touches the database.

    Returns (patient_id, test_code, collected_date, value, unit) tuples: fields trimmed,
    test_code uppercased, collected_date ISO, value a float.
    Raises ValueError whose message starts "line N:" for the first bad line
    (the header is line 1), or a ValueError if the file has no data rows.
    """
    raise NotImplementedError


def load_quarter(conn: sqlite3.Connection, site_id: str, quarter: str,
                 path: str | Path) -> str:
    """Load one site-quarter file and append one row to load_audit.

    Returns the status written to load_audit: 'loaded', 'replaced', 'skipped' or 'failed'.
    Raises ValueError (and writes no audit row) only if `quarter` is not a valid label.
    Must not leave a transaction open when it returns.
    """
    raise NotImplementedError


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    con = sqlite3.connect(":memory:")
    init_db(con)
    for site, q, name in [("s01", "2024Q1", "s01_2024Q1.csv"),
                          ("s01", "2024Q1", "s01_2024Q1_resend.csv"),
                          ("s01", "2024Q1", "s01_2024Q1_corrected.csv"),
                          ("s01", "2024Q1", "s01_2024Q1_broken.csv"),
                          ("s01", "2024Q2", "s01_2024Q2.csv"),
                          ("s02", "2024Q1", "s02_2024Q1.csv")]:
        print(name, load_quarter(con, site, q, here / "data" / name))
