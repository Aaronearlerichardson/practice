import csv
import random
import tracemalloc

import pytest

from buggy import summarize_lab_extract

HEADER = ["patient_id", "site_id", "test_code", "value", "unit", "drawn_at", "result_status"]
TARGET_BYTES = 25 * 1024 * 1024
PEAK_BUDGET_MB = 8.0  # streaming: well under 1 MB. Whole-file read: ~70+ MB.

TESTS = [("GLU", "mg/dL", 105, 25), ("CREAT", "mg/dL", 1.0, 0.3),
         ("HGB", "g/dL", 13.5, 1.8), ("A1C", "%", 6.4, 1.2), ("K", "mmol/L", 4.2, 0.5)]


def write_extract(path, target_bytes, seed=3, delimiter=","):
    """Write a synthetic lab extract of roughly target_bytes. Returns row count
    (excluding cancelled rows) for reconciliation."""
    rng = random.Random(seed)
    n_kept = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerow(HEADER)
        while f.tell() < target_bytes:
            rows = []
            for _ in range(5_000):
                code, unit, mu, sd = rng.choice(TESTS)
                r = rng.random()
                value = "" if r < 0.04 else ("<0.5" if r < 0.05 else f"{rng.gauss(mu, sd):.2f}")
                status = "cancelled" if rng.random() < 0.01 else "final"
                n_kept += status != "cancelled"
                rows.append([f"P{rng.randint(1, 200_000):07d}", "S07", code, value, unit,
                             f"2026-0{rng.randint(7, 9)}-{rng.randint(10, 28)}T08:15:00", status])
            w.writerows(rows)
    return n_kept


@pytest.fixture(scope="module")
def big_extract(tmp_path_factory):
    path = tmp_path_factory.mktemp("extract") / "S07_labs_2026Q3.csv"
    n_kept = write_extract(path, TARGET_BYTES)
    return path, n_kept


def test_small_file_summary(tmp_path):
    path = tmp_path / "small.tsv"
    rows = [
        ["P1", "S01", "GLU", "100", "mg/dL", "2026-07-01T08:00:00", "final"],
        ["P2", "S01", "GLU", "", "mg/dL", "2026-07-01T08:00:00", "final"],
        ["P3", "S01", "GLU", "140.5", "mg/dL", "2026-07-01T08:00:00", "corrected"],
        ["P4", "S01", "GLU", "999", "mg/dL", "2026-07-01T08:00:00", "cancelled"],
        ["P5", "S01", "CREAT", "<0.5", "mg/dL", "2026-07-01T08:00:00", "final"],
        ["P6", "S01", "CREAT", " 0.9 ", "mg/dL", "2026-07-01T08:00:00", "final"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(HEADER)
        w.writerows(rows)
    out = summarize_lab_extract(path, delimiter="\t")
    assert out == {
        "CREAT": {"n": 2, "n_missing": 0, "n_nonnumeric": 1, "n_numeric": 1,
                  "fill_rate": 0.5, "mean": 0.9, "min": 0.9, "max": 0.9},
        "GLU": {"n": 3, "n_missing": 1, "n_nonnumeric": 0, "n_numeric": 2,
                "fill_rate": 0.6667, "mean": 120.25, "min": 100.0, "max": 140.5},
    }


def test_big_file_reconciles(big_extract):
    path, n_kept = big_extract
    out = summarize_lab_extract(path)
    assert set(out) == {t[0] for t in TESTS}
    assert sum(s["n"] for s in out.values()) == n_kept


def test_peak_memory_budget(big_extract):
    path, _ = big_extract
    size_mb = path.stat().st_size / 2**20
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        summarize_lab_extract(path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    peak_mb = peak / 2**20
    assert peak_mb < PEAK_BUDGET_MB, (
        f"peak Python memory {peak_mb:.1f} MB on a {size_mb:.0f} MB file "
        f"(budget {PEAK_BUDGET_MB} MB, independent of file size)"
    )
