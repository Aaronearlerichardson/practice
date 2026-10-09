"""Tests for task 03. Run: python -m pytest 03_python/data_tasks/03_streaming_aggregates -q

The memory test generates a ~30 MB file in a temp dir; expect it to take 10-30 s.
"""
from __future__ import annotations

import csv
import gc
import sys
import tracemalloc
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE))
for _m in ("solution", "gen_data"):
    sys.modules.pop(_m, None)

import gen_data  # noqa: E402
from solution import REJECT_COLUMNS, SUMMARY_COLUMNS, classify, summarize  # noqa: E402

MEMORY_BUDGET_MB = 8
BIG_MB = 30

HEADER = ["row_id", "site_id", "patient_id", "test_code", "collected_date", "value", "unit"]
# (row_id, site_id, test_code, value)
SMALL = [
    (1, "S01", "GLU", "100"),
    (2, "S01", "GLU", "1e2"),         # scientific notation is a number
    (3, "S01", " glu", "130"),        # code normalized to GLU
    (4, "S01", "GLU", "NaN"),         # non_numeric
    (5, "S01", "GLU", "1000"),        # upper bound is inclusive
    (6, "S01", "GLU", "1000.01"),     # implausible
    (7, "S01", "K", " 4.5 "),         # padded value is fine
    (8, "S01", "K", "-1"),            # implausible
    (9, "S01", "K", ""),              # non_numeric
    (10, "S01", "K", "inf"),          # non_numeric (not finite)
    (11, " S02", "HBA1C", "6.5"),     # site trimmed
    (12, "S02", "hba1c", "7.5"),
    (13, "S02", "XYZ", "5"),          # unknown_test
    (14, "S03", "CREAT", "abc"),      # non_numeric
    (15, "S03", "CREAT", "50"),       # implausible
    (16, "S01", "GLU", "10"),         # lower bound is inclusive
]


def _write_small(path: Path) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for rid, site, code, value in SMALL:
            w.writerow([rid, site, f"P{rid:06d}", code, "2024-02-01", value, "u"])
    return path


def _read(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    d = tmp_path_factory.mktemp("small03")
    src = _write_small(d / "labs.csv")
    stats = summarize(src, d / "summary.csv", d / "rejects.csv")
    s_cols, s_rows = _read(d / "summary.csv")
    r_cols, r_rows = _read(d / "rejects.csv")
    return stats, s_cols, s_rows, r_cols, r_rows


# ---- exact correctness on a handcrafted file ---------------------------------

def test_small_totals(small):
    stats, *_ = small
    assert stats == {"rows_read": 16, "valid": 8, "invalid": 8}


def test_small_summary_columns_and_order(small):
    _, s_cols, s_rows, r_cols, _ = small
    assert s_cols == SUMMARY_COLUMNS
    assert r_cols == REJECT_COLUMNS
    assert [(r["site_id"], r["test_code"]) for r in s_rows] == [
        ("S01", "GLU"), ("S01", "K"), ("S02", "HBA1C"), ("S02", "XYZ"), ("S03", "CREAT"),
    ]


def test_small_summary_values(small):
    _, _, s_rows, _, _ = small
    g = {(r["site_id"], r["test_code"]): r for r in s_rows}

    glu = g[("S01", "GLU")]
    assert (int(glu["count"]), int(glu["invalid_count"])) == (5, 2)
    assert float(glu["mean"]) == pytest.approx(268.0, abs=1e-4)
    assert (float(glu["min"]), float(glu["max"])) == (10.0, 1000.0)

    k = g[("S01", "K")]
    assert (int(k["count"]), int(k["invalid_count"])) == (1, 3)
    assert float(k["mean"]) == pytest.approx(4.5)

    a1c = g[("S02", "HBA1C")]
    assert (int(a1c["count"]), int(a1c["invalid_count"])) == (2, 0)
    assert float(a1c["mean"]) == pytest.approx(7.0)
    assert (float(a1c["min"]), float(a1c["max"])) == (6.5, 7.5)

    for key in [("S02", "XYZ"), ("S03", "CREAT")]:
        row = g[key]
        assert int(row["count"]) == 0
        assert (row["mean"], row["min"], row["max"]) == ("", "", "")
    assert int(g[("S02", "XYZ")]["invalid_count"]) == 1
    assert int(g[("S03", "CREAT")]["invalid_count"]) == 2


def test_mean_has_four_decimals(small):
    _, _, s_rows, _, _ = small
    for r in s_rows:
        if r["mean"]:
            assert len(r["mean"].split(".")[1]) == 4


def test_small_rejects(small):
    *_, r_rows = small
    assert [(int(r["row_id"]), r["reason"]) for r in r_rows] == [
        (4, "non_numeric"), (6, "implausible"), (8, "implausible"), (9, "non_numeric"),
        (10, "non_numeric"), (13, "unknown_test"), (14, "non_numeric"), (15, "implausible"),
    ]
    by_id = {int(r["row_id"]): r for r in r_rows}
    assert by_id[9]["value"] == ""            # raw values, unmodified
    assert by_id[4]["value"] == "NaN"
    assert by_id[13]["test_code"] == "XYZ"
    assert by_id[6]["patient_id"] == "P000006"


@pytest.mark.parametrize("code,value,expected", [
    ("GLU", "100", (100.0, None)),
    ("GLU", " 1e2 ", (100.0, None)),
    ("GLU", "10", (10.0, None)),
    ("GLU", "9.99", (None, "implausible")),
    ("GLU", "nan", (None, "non_numeric")),
    ("GLU", "-inf", (None, "non_numeric")),
    ("GLU", "", (None, "non_numeric")),
    ("LDL", "100", (None, "unknown_test")),
    ("LDL", "abc", (None, "unknown_test")),   # unknown_test is checked first
    ("K", "10.0", (10.0, None)),
])
def test_classify(code, value, expected):
    assert classify(code, value) == expected


def test_sample_file_reconciles(tmp_path):
    stats = summarize(DATA / "labs_sample.csv", tmp_path / "s.csv", tmp_path / "r.csv")
    assert stats == {"rows_read": 300, "valid": 288, "invalid": 12}
    _, s_rows = _read(tmp_path / "s.csv")
    _, r_rows = _read(tmp_path / "r.csv")
    assert sum(int(r["count"]) for r in s_rows) == 288
    assert sum(int(r["invalid_count"]) for r in s_rows) == 12 == len(r_rows)


# ---- constant memory on a generated file -------------------------------------

@pytest.fixture(scope="module")
def big(tmp_path_factory):
    d = tmp_path_factory.mktemp("big03")
    path = d / "labs_big.csv"
    truth = gen_data.write_big(path, BIG_MB)
    return d, path, truth


def test_big_file_constant_memory_and_reconciles(big):
    d, path, truth = big
    assert path.stat().st_size >= BIG_MB * 1_000_000 and truth["rows"] > 300_000
    gc.collect()
    tracemalloc.start()
    try:
        stats = summarize(path, d / "summary.csv", d / "rejects.csv")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    peak_mb = peak / 1e6
    assert peak_mb < MEMORY_BUDGET_MB, f"peak {peak_mb:.1f} MB for a {BIG_MB} MB file"

    assert stats == {"rows_read": truth["rows"], "valid": truth["valid"],
                     "invalid": truth["invalid"]}
    _, s_rows = _read(d / "summary.csv")
    assert sum(int(r["count"]) + int(r["invalid_count"]) for r in s_rows) == truth["rows"]
    # 12 sites x (6 tests + the unknown LDL code), nothing else
    assert len(s_rows) == 12 * 7
    with open(d / "rejects.csv", newline="", encoding="utf-8") as f:
        reasons = Counter(r["reason"] for r in csv.DictReader(f))
    assert dict(reasons) == truth["by_reason"]
