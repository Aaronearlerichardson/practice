"""Tests for task 01. Run: python -m pytest 03_python/data_tasks/01_multisite_lab_join -q"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE))
sys.modules.pop("solution", None)

from solution import (  # noqa: E402
    REJECT_COLUMNS, STANDARD_COLUMNS, load_crosswalk, load_mappings, read_site, run,
)


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    out = tmp_path_factory.mktemp("out01")
    result = run(DATA, out)
    std_cols, std = _read(out / "labs_standardized.csv")
    rej_cols, rej = _read(out / "labs_rejects.csv")
    return result, std_cols, std, rej_cols, rej


def _by_source(rows):
    return {(r["site_id"], int(r["source_row"])): r for r in rows}


# ---- whole-run shape -------------------------------------------------------

def test_counts_returned_and_written(outputs):
    result, _, std, _, rej = outputs
    assert result == {"written": 84, "rejected": 13}
    assert len(std) == 84
    assert len(rej) == 13


def test_every_input_row_lands_exactly_once(outputs):
    _, _, std, _, rej = outputs
    keys = [(r["site_id"], int(r["source_row"])) for r in std + rej]
    assert len(keys) == len(set(keys)) == 40 + 33 + 24


def test_column_order(outputs):
    _, std_cols, _, rej_cols, _ = outputs
    assert std_cols == STANDARD_COLUMNS
    assert rej_cols == REJECT_COLUMNS


def test_per_site_written_counts(outputs):
    _, _, std, _, _ = outputs
    assert Counter(r["site_id"] for r in std) == {"site_a": 34, "site_b": 29, "site_c": 21}


def test_reject_reason_counts(outputs):
    _, _, _, _, rej = outputs
    assert Counter(r["reject_reason"] for r in rej) == {
        "unmapped_test": 3, "unknown_patient": 2, "bad_date": 4, "non_numeric_value": 4,
    }


def test_output_sorted(outputs):
    _, _, std, _, rej = outputs
    key = [(r["patient_id"], r["collected_date"], r["test_code"], r["site_id"],
            int(r["source_row"])) for r in std]
    assert key == sorted(key)
    rkey = [(r["site_id"], int(r["source_row"])) for r in rej]
    assert rkey == sorted(rkey)


def test_standardized_values_are_clean(outputs):
    _, _, std, _, _ = outputs
    for r in std:
        assert r["patient_id"].startswith("P") and len(r["patient_id"]) == 5
        assert r["test_code"] in {"GLU", "HBA1C", "K", "CREAT", "HGB"}
        assert len(r["collected_date"]) == 10 and r["collected_date"][4] == "-"
        assert r["unit"] == r["unit"].strip() and r["unit"]
        float(r["value"])


# ---- planted traps ---------------------------------------------------------

def test_crosswalk_duplicate_does_not_fan_out(outputs):
    _, _, std, _, _ = outputs
    assert sum(r["patient_id"] == "P0003" for r in std) == 4


def test_messy_codes_and_ids_still_map(outputs):
    _, _, std, _, _ = outputs
    s = _by_source(std)
    assert s[("site_a", 4)]["test_code"] == "GLU"            # "  glucose, fasting "
    assert s[("site_a", 22)]["patient_id"] == "P0003"        # " a1003"
    assert s[("site_b", 3)]["test_code"] == "HBA1C"          # "a1c"
    assert s[("site_b", 15)]["patient_id"] == "P0007"        # "b-0203"
    assert s[("site_b", 24)]["test_code"] == "K"             # " k+ "
    assert s[("site_c", 14)]["test_code"] == "HBA1C"         # "HbA1c_Pct"
    assert float(s[("site_b", 21)]["value"]) == 5.1          # " 5.1 "


def test_dates_converted_per_site_format(outputs):
    _, _, std, _, _ = outputs
    s = _by_source(std)
    assert s[("site_b", 24)]["collected_date"] == "2024-03-28"   # 03/28/2024
    assert s[("site_c", 14)]["collected_date"] == "2024-03-18"   # timestamp -> date
    assert s[("site_a", 4)]["collected_date"] == "2024-01-15"


def test_quoted_comment_survives(outputs):
    _, _, std, _, _ = outputs
    row = _by_source(std)[("site_a", 19)]
    assert row["comment"] == 'hemolyzed, "redraw" requested'
    assert row["patient_id"] == "P0006"
    assert row["test_code"] == "HBA1C"
    assert float(row["value"]) == 6.4
    assert _by_source(std)[("site_b", 24)]["comment"] == "repeat, hemolyzed"


def test_specific_rejects(outputs):
    _, _, _, _, rej = outputs
    r = _by_source(rej)
    expected = {
        ("site_a", 7): "unmapped_test",
        ("site_a", 10): "unknown_patient",
        ("site_a", 13): "bad_date",          # month 13
        ("site_a", 16): "non_numeric_value",  # "pending"
        ("site_a", 25): "non_numeric_value",  # "NaN"
        ("site_a", 28): "unmapped_test",      # also unknown patient: first rule wins
        ("site_b", 6): "unmapped_test",
        ("site_b", 9): "bad_date",            # 02/30/2024
        ("site_b", 12): "bad_date",           # ISO date at a US-format site
        ("site_b", 18): "non_numeric_value",  # empty
        ("site_c", 2): "non_numeric_value",   # parquet null
        ("site_c", 6): "bad_date",
        ("site_c", 10): "unknown_patient",
    }
    assert {k: v["reject_reason"] for k, v in r.items()} == expected


def test_reject_rows_keep_raw_values(outputs):
    _, _, _, _, rej = outputs
    r = _by_source(rej)
    assert r[("site_a", 25)]["local_test_name"] == "Glucose, Fasting"
    assert r[("site_a", 25)]["value"] == "NaN"
    assert r[("site_b", 9)]["collected_date"] == "02/30/2024"
    assert r[("site_c", 10)]["local_patient_id"] == "9999"
    assert r[("site_c", 2)]["value"] == ""


# ---- building blocks -------------------------------------------------------

def test_load_crosswalk_normalizes_and_dedupes():
    xw = load_crosswalk(DATA / "patient_crosswalk.csv")
    assert len(xw) == 30
    assert xw[("site_a", "A1003")] == "P0003"
    assert xw[("site_b", "B-0201")] == "P0005"
    assert xw[("site_c", "4410")] == "P0040"


def test_load_crosswalk_conflict_raises(tmp_path):
    p = tmp_path / "xw.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site_id", "local_patient_id", "patient_id"])
        w.writerow(["site_a", "A1", "P0001"])
        w.writerow(["site_a", " a1", "P0002"])
    with pytest.raises(ValueError):
        load_crosswalk(p)


def test_read_site_parquet_returns_strings():
    mappings = load_mappings(DATA / "mappings.json")
    rows = read_site(DATA, "site_c", mappings["site_c"])
    assert len(rows) == 24
    assert set(rows[0]) == {"local_patient_id", "local_test_name", "value", "unit",
                            "collected_date", "comment", "source_row"}
    assert rows[1]["local_patient_id"] == "4410"
    assert rows[1]["value"] == ""
    assert rows[1]["source_row"] == "2"
    assert all(r["comment"] == "" for r in rows)
    assert all(isinstance(v, str) for r in rows for v in r.values())


def test_read_site_tsv_keeps_raw_text():
    mappings = load_mappings(DATA / "mappings.json")
    rows = read_site(DATA, "site_b", mappings["site_b"])
    assert len(rows) == 33
    assert rows[20]["value"] == " 5.1 "
    assert rows[23]["local_test_name"] == " k+ "
