"""Time normalize_labs at increasing sizes against the budget.

    python 03_python\\debugging\\05_lab_unit_normalize\\bench.py

Target: 2,000,000 lab rows (one large site's quarterly lab extract) in < 5 s.
Stops early once a size goes over the budget.
"""
import time

import numpy as np
import pandas as pd

from buggy import normalize_labs

TARGET_N = 2_000_000
BUDGET_S = 5.0

PAIRS = [("glucose", "mg/dL", 100, 30), ("glucose", "mmol/L", 5.6, 1.5),
         ("creatinine", "mg/dL", 1.0, 0.4), ("creatinine", "umol/L", 90, 30),
         ("cholesterol", "mg/dL", 190, 40), ("hemoglobin", "g/L", 135, 20),
         ("hemoglobin", "g/dL", 13.5, 2), ("hba1c", "%", 6.5, 1.5),
         ("glucose", "mg/dl", 100, 30)]


def make_labs(n, seed=11):
    rng = np.random.default_rng(seed)
    which = rng.integers(0, len(PAIRS), n)
    values = rng.normal(np.array([p[2] for p in PAIRS])[which],
                        np.array([p[3] for p in PAIRS])[which])
    values[rng.random(n) < 0.03] = np.nan
    return pd.DataFrame({
        "lab_id": np.arange(n),
        "test_code": np.array([p[0] for p in PAIRS], dtype=object)[which],
        "unit": np.array([p[1] for p in PAIRS], dtype=object)[which],
        "value": values,
    })


def main():
    print(f"target: {TARGET_N:,} rows in < {BUDGET_S} s")
    for n in (10_000, 50_000, 200_000, 500_000, 2_000_000):
        labs = make_labs(n)
        t0 = time.perf_counter()
        normalize_labs(labs)
        elapsed = time.perf_counter() - t0
        print(f"{n:>10,} rows  {elapsed:8.3f} s  ({elapsed / n * 1e6:.2f} us/row)")
        if elapsed > BUDGET_S:
            print(f"over budget at {n:,} rows; stopping")
            return
    print("within budget at target size")


if __name__ == "__main__":
    main()
