from datetime import datetime

import pytest

import buggy
from buggy import load_batch, reconcile

HEADER = "encounter_id,patient_id,admit_ts,discharge_ts,weight_kg"
LINES = [
    # line 2..: valid rows, old export format (no seconds)
    "E001,P001,2026-07-01 08:15,2026-07-03 11:00,72.5",
    "E002,P002,2026-07-01 09:40,,",
    "E003,P003,2026-07-02 14:05,2026-07-02 18:30,101.3",
    # valid rows from the site's new EHR export (with seconds)
    "E004,P004,2026-07-03 07:12:45,2026-07-04 10:00:00,64.0",
    "E005,P005,2026-07-03 22:01:09,,88.8",
    # genuinely bad rows
    "E006,,2026-07-04 10:00,2026-07-05 10:00,70.0",           # line 7: no patient
    "E007,P007,07/04/2026 10:00,,70.0",                        # line 8: bad date format
    "E008,P008,2026-07-05 10:00,2026-07-04 09:00,70.0",        # line 9: discharge < admit
    "E009,P009,2026-07-05 12:00,,seventy",                     # line 10: bad weight
    "E010,P010,2026-07-06 08:00",                              # line 11: short row
    "E011,P011,2026-07-06 09:30,2026-07-06 15:00,55.2",
]
MANIFEST_ROWS = len(LINES)


@pytest.fixture
def batch_path(tmp_path):
    p = tmp_path / "S04_encounters_2026Q3.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        f.write("\r\n".join([HEADER, *LINES]) + "\r\n")
    return p


def test_valid_rows_are_loaded(batch_path):
    result = load_batch(batch_path)
    assert [r["encounter_id"] for r in result.rows] == ["E001", "E002", "E003", "E004", "E005", "E011"]
    e004 = result.rows[3]
    assert e004["admit_ts"] == datetime(2026, 7, 3, 7, 12, 45)
    assert e004["weight_kg"] == 64.0
    assert result.rows[1]["discharge_ts"] is None and result.rows[1]["weight_kg"] is None


def test_rejects_have_line_numbers_and_reasons(batch_path):
    result = load_batch(batch_path)
    by_line = {r["line_no"]: r["reason"] for r in result.rejects}
    assert sorted(by_line) == [7, 8, 9, 10, 11]
    assert "patient_id" in by_line[7]
    assert "admit_ts" in by_line[8]
    assert "discharge_ts" in by_line[9]
    assert "weight_kg" in by_line[10]
    assert "column" in by_line[11]
    assert all(r["raw"] for r in result.rejects)


def test_reconciles_with_manifest(batch_path):
    result = load_batch(batch_path)
    rec = reconcile(result, MANIFEST_ROWS)
    assert rec == {"manifest_rows": 11, "loaded": 6, "rejected": 5, "ok": True}


def test_reconcile_flags_lost_rows(batch_path):
    result = load_batch(batch_path)
    result.rows.pop()  # a row disappeared without becoming a reject
    assert reconcile(result, MANIFEST_ROWS)["ok"] is False


def test_programming_errors_are_not_swallowed(batch_path, monkeypatch):
    def broken(raw):
        raise TypeError("bug in parser, not bad data")
    monkeypatch.setattr(buggy, "parse_row", broken)
    with pytest.raises(TypeError):
        load_batch(batch_path)
