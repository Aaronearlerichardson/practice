import csv
import random
import subprocess
import sys
from pathlib import Path

from buggy import dedupe_encounters, dedupe_report, read_batches

PERF_N = 40_000
PERF_BUDGET_S = 1.0  # fixed version: ~0.05 s. Quadratic version: 10+ s.


def make_rows(n, dup_rate=0.1, seed=7):
    """Synthetic encounters; ~dup_rate of rows repeat an earlier key."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        if rows and rng.random() < dup_rate:
            src = rng.choice(rows)
            rows.append({**src, "source_file": "resend.csv"})
        else:
            rows.append({
                "site_id": f"S{rng.randint(1, 12):02d}",
                "patient_id": f"P{rng.randint(1, 10**7):07d}",
                "encounter_id": f"E{i:08d}",
                "source_file": "q3.csv",
            })
    return rows


MAKE, FUNC = "make_rows", "dedupe_encounters"
HERE = Path(__file__).resolve().parent

# The timed call runs in a child process so a slow version can be killed at
# the timeout instead of hanging the test run.
_CHILD = """
import sys, time
sys.path.insert(0, sys.argv[1])
from {module} import {make}
from buggy import {func}
data = {make}(int(sys.argv[2]))
t0 = time.perf_counter()
{func}(data)
print(time.perf_counter() - t0)
"""


def time_in_subprocess(n, timeout):
    """Seconds the timed call took in a fresh process, or None on timeout."""
    code = _CHILD.format(module=Path(__file__).stem, make=MAKE, func=FUNC)
    try:
        proc = subprocess.run([sys.executable, "-c", code, str(HERE), str(n)],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    assert proc.returncode == 0, proc.stderr
    return float(proc.stdout.strip().splitlines()[-1])


def test_keeps_first_occurrence_in_order():
    rows = [
        {"site_id": "S01", "patient_id": "P1", "encounter_id": "E1", "source_file": "q2.csv"},
        {"site_id": "S01", "patient_id": "P2", "encounter_id": "E2", "source_file": "q2.csv"},
        {"site_id": "S01", "patient_id": "P1", "encounter_id": "E1", "source_file": "q3.csv"},
        {"site_id": "S02", "patient_id": "P1", "encounter_id": "E1", "source_file": "q3.csv"},
        {"site_id": "s01 ", "patient_id": "p2", "encounter_id": "e2", "source_file": "q3.csv"},
        {"site_id": "S01", "patient_id": "P3", "encounter_id": "E3", "source_file": "q3.csv"},
    ]
    kept = dedupe_encounters(rows)
    assert [(r["site_id"], r["encounter_id"], r["source_file"]) for r in kept] == [
        ("S01", "E1", "q2.csv"),
        ("S01", "E2", "q2.csv"),
        ("S02", "E1", "q3.csv"),
        ("S01", "E3", "q3.csv"),
    ]


def test_report_counts():
    rows = make_rows(2_000)
    expected_unique = len({(r["site_id"], r["patient_id"], r["encounter_id"]) for r in rows})
    report = dedupe_report(rows)
    assert report["n_input"] == 2_000
    assert report["n_kept"] == expected_unique
    assert report["n_duplicates_dropped"] == 2_000 - expected_unique


def test_read_batches_tags_source(tmp_path):
    for name, ids in (("q2.csv", ["E1", "E2"]), ("q3.csv", ["E2", "E3"])):
        with open(tmp_path / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["site_id", "patient_id", "encounter_id"])
            for e in ids:
                w.writerow(["S01", "P1", e])
    rows = read_batches([tmp_path / "q2.csv", tmp_path / "q3.csv"])
    kept = dedupe_encounters(rows)
    assert [(r["encounter_id"], r["source_file"]) for r in kept] == [
        ("E1", "q2.csv"), ("E2", "q2.csv"), ("E3", "q3.csv"),
    ]


def test_perf_budget():
    # child timeout = budget + allowance for interpreter/import start-up
    elapsed = time_in_subprocess(PERF_N, timeout=PERF_BUDGET_S + 5)
    assert elapsed is not None, (
        f"dedupe_encounters on {PERF_N:,} rows was killed after {PERF_BUDGET_S + 5:.0f} s "
        f"(budget {PERF_BUDGET_S} s)"
    )
    assert elapsed < PERF_BUDGET_S, (
        f"dedupe_encounters on {PERF_N:,} rows took {elapsed:.2f} s (budget {PERF_BUDGET_S} s)"
    )
