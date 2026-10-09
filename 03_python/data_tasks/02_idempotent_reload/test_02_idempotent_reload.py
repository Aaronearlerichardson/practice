"""Tests for task 02. Run: python -m pytest 03_python/data_tasks/02_idempotent_reload -q"""
from __future__ import annotations

import csv
import hashlib
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE))
sys.modules.pop("solution", None)

from solution import (  # noqa: E402
    file_checksum, init_db, load_quarter, parse_quarter, read_and_validate,
)

Q1 = DATA / "s01_2024Q1.csv"
Q1_RESEND = DATA / "s01_2024Q1_resend.csv"
Q1_FIX = DATA / "s01_2024Q1_corrected.csv"
Q1_BROKEN = DATA / "s01_2024Q1_broken.csv"
Q2 = DATA / "s01_2024Q2.csv"
S02_Q1 = DATA / "s02_2024Q1.csv"


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(tmp_path / "labs.db")
    init_db(c)
    yield c
    c.close()


def stored(conn, site, quarter):
    return sorted(conn.execute(
        "SELECT patient_id, test_code, collected_date, value, unit FROM lab_results"
        " WHERE site_id=? AND quarter=?", (site, quarter)).fetchall())


def expected(path):
    with open(path, newline="", encoding="utf-8") as f:
        return sorted((r["patient_id"], r["test_code"], r["collected_date"], float(r["value"]),
                       r["unit"]) for r in csv.DictReader(f))


def audit(conn):
    return conn.execute("SELECT site_id, quarter, file_name, checksum, row_count, status, message"
                        " FROM load_audit ORDER BY load_id").fetchall()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, header=("patient_id", "test_code", "collected_date", "value", "unit")):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerows(rows)
    return path


# ---- building blocks -------------------------------------------------------

def test_parse_quarter():
    assert parse_quarter("2024Q1") == (date(2024, 1, 1), date(2024, 4, 1))
    assert parse_quarter("2024Q3") == (date(2024, 7, 1), date(2024, 10, 1))
    assert parse_quarter("2024Q4") == (date(2024, 10, 1), date(2025, 1, 1))
    for bad in ["2024Q5", "2024Q0", "24Q1", "2024-Q1", "2024q1", ""]:
        with pytest.raises(ValueError):
            parse_quarter(bad)


def test_file_checksum_is_sha256_of_bytes():
    assert file_checksum(Q1) == sha(Q1)
    assert file_checksum(Q1) == file_checksum(Q1_RESEND)
    assert file_checksum(Q1) != file_checksum(Q1_FIX)


def test_init_db_is_idempotent(conn):
    init_db(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"lab_results", "load_audit"} <= tables


def test_read_and_validate_quarter_edges():
    rows = read_and_validate(Q1, "2024Q1")
    assert len(rows) == 60
    dates = {r[2] for r in rows}
    assert "2024-01-01" in dates and "2024-03-31" in dates
    with pytest.raises(ValueError, match=r"^line 41:"):
        read_and_validate(Q1_BROKEN, "2024Q1")


def test_read_and_validate_normalizes(tmp_path):
    p = write_csv(tmp_path / "x.csv", [[" P0001 ", " glu ", "2024-02-01", " 99 ", " mg/dL "]])
    assert read_and_validate(p, "2024Q1") == [("P0001", "GLU", "2024-02-01", 99.0, "mg/dL")]


@pytest.mark.parametrize("bad_row", [
    ["P0001", "GLU", "2024-02-30", "99", "mg/dL"],    # not a date
    ["P0001", "GLU", "02/01/2024", "99", "mg/dL"],    # not ISO
    ["P0001", "GLU", "2023-12-31", "99", "mg/dL"],    # previous quarter
    ["P0001", "GLU", "2024-02-01", "abc", "mg/dL"],
    ["P0001", "GLU", "2024-02-01", "nan", "mg/dL"],
    ["", "GLU", "2024-02-01", "99", "mg/dL"],
    ["P0001", "", "2024-02-01", "99", "mg/dL"],
    ["P0001", "GLU", "2024-02-01", "99"],             # 4 fields
])
def test_read_and_validate_rejects_bad_line(tmp_path, bad_row):
    good = ["P0002", "K", "2024-02-02", "4.1", "mmol/L"]
    p = write_csv(tmp_path / "x.csv", [good, bad_row, good])
    with pytest.raises(ValueError, match=r"^line 3:"):
        read_and_validate(p, "2024Q1")


# ---- load_quarter behaviour --------------------------------------------------

def test_first_load(conn):
    assert load_quarter(conn, "s01", "2024Q1", Q1) == "loaded"
    assert stored(conn, "s01", "2024Q1") == expected(Q1)
    assert len(stored(conn, "s01", "2024Q1")) == 60
    assert audit(conn) == [("s01", "2024Q1", "s01_2024Q1.csv", sha(Q1), 60, "loaded", "")]
    assert not conn.in_transaction


def test_identical_resend_is_skipped(conn):
    load_quarter(conn, "s01", "2024Q1", Q1)
    before = stored(conn, "s01", "2024Q1")
    assert load_quarter(conn, "s01", "2024Q1", Q1_RESEND) == "skipped"
    assert stored(conn, "s01", "2024Q1") == before
    a = audit(conn)
    assert len(a) == 2
    assert a[1][:6] == ("s01", "2024Q1", "s01_2024Q1_resend.csv", sha(Q1), 0, "skipped")
    assert not conn.in_transaction


def test_corrected_resend_replaces(conn):
    load_quarter(conn, "s01", "2024Q1", Q1)
    assert load_quarter(conn, "s01", "2024Q1", Q1_FIX) == "replaced"
    got = stored(conn, "s01", "2024Q1")
    assert got == expected(Q1_FIX)
    assert len(got) == 59
    assert ("P0024", "CREAT", "2024-02-29", 1.07, "mg/dL") in got        # added row
    assert ("P0022", "HBA1C", "2024-03-07", 8.0, "%") not in got          # withdrawn row
    assert ("P0020", "HBA1C", "2024-03-21", 6.1, "%") in got              # corrected row
    assert audit(conn)[-1][4:6] == (59, "replaced")


def test_replace_touches_only_that_site_quarter(conn):
    assert load_quarter(conn, "s02", "2024Q1", S02_Q1) == "loaded"
    assert load_quarter(conn, "s01", "2024Q2", Q2) == "loaded"
    load_quarter(conn, "s01", "2024Q1", Q1)
    other_site, other_q = stored(conn, "s02", "2024Q1"), stored(conn, "s01", "2024Q2")
    load_quarter(conn, "s01", "2024Q1", Q1_FIX)
    assert stored(conn, "s02", "2024Q1") == other_site == expected(S02_Q1)
    assert stored(conn, "s01", "2024Q2") == other_q == expected(Q2)
    assert conn.execute("SELECT COUNT(*) FROM lab_results").fetchone()[0] == 40 + 55 + 59


def test_broken_file_fails_and_keeps_prior_data(conn):
    load_quarter(conn, "s01", "2024Q1", Q1)
    load_quarter(conn, "s01", "2024Q1", Q1_FIX)
    assert load_quarter(conn, "s01", "2024Q1", Q1_BROKEN) == "failed"
    assert stored(conn, "s01", "2024Q1") == expected(Q1_FIX)
    last = audit(conn)[-1]
    assert last[2] == "s01_2024Q1_broken.csv"
    assert last[4:6] == (0, "failed")
    assert "line 41" in last[6]
    assert not conn.in_transaction


def test_failed_load_is_not_the_current_version(conn):
    assert load_quarter(conn, "s01", "2024Q1", Q1_BROKEN) == "failed"
    assert stored(conn, "s01", "2024Q1") == []
    assert load_quarter(conn, "s01", "2024Q1", Q1_BROKEN) == "failed"   # not 'skipped'
    assert load_quarter(conn, "s01", "2024Q1", Q1) == "loaded"          # not 'replaced'
    assert [r[5] for r in audit(conn)] == ["failed", "failed", "loaded"]


def test_resend_of_an_older_version_replaces(conn):
    load_quarter(conn, "s01", "2024Q1", Q1)
    load_quarter(conn, "s01", "2024Q1", Q1_FIX)
    assert load_quarter(conn, "s01", "2024Q1", Q1_RESEND) == "replaced"
    assert stored(conn, "s01", "2024Q1") == expected(Q1)
    assert load_quarter(conn, "s01", "2024Q1", Q1) == "skipped"


def test_same_file_for_another_site_is_not_skipped(conn):
    load_quarter(conn, "s01", "2024Q1", Q1)
    assert load_quarter(conn, "s03", "2024Q1", Q1) == "loaded"
    assert stored(conn, "s03", "2024Q1") == stored(conn, "s01", "2024Q1")


def test_header_only_file_fails_without_wiping(conn, tmp_path):
    load_quarter(conn, "s01", "2024Q1", Q1)
    empty = write_csv(tmp_path / "empty.csv", [])
    assert load_quarter(conn, "s01", "2024Q1", empty) == "failed"
    assert len(stored(conn, "s01", "2024Q1")) == 60


def test_wrong_header_fails(conn, tmp_path):
    p = write_csv(tmp_path / "h.csv", [["P0001", "GLU", "2024-02-01", "99", "mg/dL"]],
                  header=("patient", "test_code", "collected_date", "value", "unit"))
    assert load_quarter(conn, "s01", "2024Q1", p) == "failed"
    assert stored(conn, "s01", "2024Q1") == []


def test_bad_quarter_label_raises_without_audit(conn):
    with pytest.raises(ValueError):
        load_quarter(conn, "s01", "2024Q5", Q1)
    assert audit(conn) == []


def test_database_error_mid_write_rolls_back(conn, tmp_path):
    load_quarter(conn, "s01", "2024Q1", Q1)
    conn.execute("CREATE TRIGGER boom BEFORE INSERT ON lab_results"
                 " WHEN NEW.patient_id = 'P9999' BEGIN SELECT RAISE(ABORT, 'boom'); END")
    conn.commit()
    with open(Q1_FIX, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    p = write_csv(tmp_path / "s01_2024Q1_v3.csv",
                  rows + [["P9999", "GLU", "2024-03-30", "100", "mg/dL"]])
    assert load_quarter(conn, "s01", "2024Q1", p) == "failed"
    assert stored(conn, "s01", "2024Q1") == expected(Q1)   # the delete was rolled back too
    assert audit(conn)[-1][5] == "failed"
    assert not conn.in_transaction
    # the failed attempt must not become "current": dropping the trigger and retrying loads it
    conn.execute("DROP TRIGGER boom")
    conn.commit()
    assert load_quarter(conn, "s01", "2024Q1", p) == "replaced"
    assert len(stored(conn, "s01", "2024Q1")) == 60


def test_changes_survive_reconnect(tmp_path):
    db = tmp_path / "persist.db"
    c = sqlite3.connect(db)
    init_db(c)
    load_quarter(c, "s01", "2024Q1", Q1)
    load_quarter(c, "s01", "2024Q1", Q1_BROKEN)
    c.close()
    c2 = sqlite3.connect(db)
    assert len(stored(c2, "s01", "2024Q1")) == 60
    assert [r[5] for r in audit(c2)] == ["loaded", "failed"]
    c2.close()
