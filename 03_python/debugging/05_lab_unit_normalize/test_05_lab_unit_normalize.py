import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from buggy import normalize_labs, plausibility_summary

PERF_N = 100_000
PERF_BUDGET_S = 0.5  # vectorized: ~0.05 s. Row-by-row: several seconds.


def make_labs(n, seed=11):
    rng = np.random.default_rng(seed)
    pairs = [("glucose", "mg/dL", 100, 30), ("glucose", "mmol/L", 5.6, 1.5),
             ("creatinine", "mg/dL", 1.0, 0.4), ("creatinine", "umol/L", 90, 30),
             ("cholesterol", "mg/dL", 190, 40), ("hemoglobin", "g/L", 135, 20),
             ("hemoglobin", "g/dL", 13.5, 2), ("hba1c", "%", 6.5, 1.5),
             ("glucose", "mg/dl", 100, 30)]  # unknown unit spelling
    which = rng.integers(0, len(pairs), n)
    tests = np.array([p[0] for p in pairs], dtype=object)[which]
    units = np.array([p[1] for p in pairs], dtype=object)[which]
    mu = np.array([p[2] for p in pairs])[which]
    sd = np.array([p[3] for p in pairs])[which]
    values = rng.normal(mu, sd)
    values[rng.random(n) < 0.03] = np.nan
    values[rng.random(n) < 0.01] *= 100  # unit/entry errors
    return pd.DataFrame({
        "lab_id": [f"L{i:07d}" for i in range(n)],
        "test_code": tests,
        "unit": units,
        "value": values,
    })


MAKE, FUNC = "make_labs", "normalize_labs"
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


def small_labs():
    return pd.DataFrame({
        "lab_id": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
        "test_code": ["glucose", " Glucose", "creatinine", "hemoglobin",
                      "hba1c", "glucose", "cholesterol", "potassium"],
        "unit": ["mg/dL", "mmol/L", "mg/dL", "g/L", "%", "mg/dl", "mg/dL", "mmol/L"],
        "value": [126.0, 7.1, 1.2, 142.0, 25.0, 99.0, np.nan, 4.1],
    }, index=[10, 11, 12, 13, 14, 15, 16, 17])  # non-default index on purpose


def test_small_frame_values():
    out = normalize_labs(small_labs())
    expected_value = [126 / 18.016, 7.1, 1.2 * 88.42, 14.2, 25.0, None, None, None]
    for got, exp in zip(out["value_std"], expected_value):
        if exp is None:
            assert pd.isna(got)
        else:
            assert got == pytest.approx(exp, rel=1e-9)
    assert list(out["unit_std"].where(out["unit_std"].notna(), "")) == [
        "mmol/L", "mmol/L", "umol/L", "g/dL", "%", "", "mmol/L", ""]
    assert list(out["plausible"]) == [True, True, True, True, False, False, False, False]
    assert list(out["qc_reason"]) == ["", "", "", "", "out_of_range",
                                      "unknown_unit", "missing_value", "unknown_unit"]
    assert list(out.index) == list(small_labs().index)


def test_input_not_modified():
    labs = small_labs()
    before = labs.copy()
    normalize_labs(labs)
    pd.testing.assert_frame_equal(labs, before)


def test_summary():
    summary = plausibility_summary(normalize_labs(small_labs()))
    assert summary.loc["glucose", "n"] == 3
    assert math.isclose(summary.loc["glucose", "plausible_rate"], 0.6667)


def test_large_frame_reason_counts():
    out = normalize_labs(make_labs(5_000))
    counts = out["qc_reason"].value_counts().to_dict()
    assert sum(counts.values()) == 5_000
    assert counts["unknown_unit"] > 400
    assert counts["missing_value"] > 50
    assert counts["out_of_range"] > 30
    assert (out["plausible"] == (out["qc_reason"] == "")).all()


def test_perf_budget():
    # child timeout = budget + allowance for interpreter/import start-up
    elapsed = time_in_subprocess(PERF_N, timeout=PERF_BUDGET_S + 5)
    assert elapsed is not None, (
        f"normalize_labs on {PERF_N:,} rows was killed after {PERF_BUDGET_S + 5:.0f} s "
        f"(budget {PERF_BUDGET_S} s)"
    )
    assert elapsed < PERF_BUDGET_S, (
        f"normalize_labs on {PERF_N:,} rows took {elapsed:.2f} s (budget {PERF_BUDGET_S} s)"
    )
