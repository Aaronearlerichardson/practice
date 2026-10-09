"""Time dedupe_encounters at increasing sizes against the budget.

    python 03_python\\debugging\\03_slow_encounter_dedup\\bench.py

Target: 1,000,000 rows in under 5 s (a site's full quarterly encounter file).
Stops early once a size goes over the budget.
"""
import random
import time

from buggy import dedupe_encounters

TARGET_N = 1_000_000
BUDGET_S = 5.0


def make_rows(n, dup_rate=0.1, seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        if rows and rng.random() < dup_rate:
            rows.append(dict(rng.choice(rows)))
        else:
            rows.append({
                "site_id": f"S{rng.randint(1, 12):02d}",
                "patient_id": f"P{rng.randint(1, 10**7):07d}",
                "encounter_id": f"E{i:08d}",
            })
    return rows


def main():
    print(f"target: {TARGET_N:,} rows in < {BUDGET_S} s")
    for n in (5_000, 10_000, 20_000, 40_000, 100_000, 300_000, 1_000_000):
        rows = make_rows(n)
        t0 = time.perf_counter()
        kept = dedupe_encounters(rows)
        elapsed = time.perf_counter() - t0
        print(f"{n:>10,} rows  {elapsed:8.3f} s  kept={len(kept):,}")
        if elapsed > BUDGET_S:
            print(f"over budget at {n:,} rows; stopping")
            return
    print("within budget at target size")


if __name__ == "__main__":
    main()
