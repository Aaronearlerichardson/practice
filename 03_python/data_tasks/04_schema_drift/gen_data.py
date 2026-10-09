"""Generate four quarterly lab extracts from one site, with schema drift planted, for task 04.

Fixed seed: `python gen_data.py` rewrites data/ byte-identically.
All data is synthetic. No real patients.

The drift is planted in build_quarter(). Find it with your code before you read this file.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEED = 404
N = 100

TESTS = {"GLU": ("mg/dL", 70, 180), "HBA1C": ("%", 4.8, 9.5), "K": ("mmol/L", 3.4, 5.2),
         "CREAT": ("mg/dL", 0.6, 1.4), "HGB": ("g/dL", 11.0, 16.5)}
CODES = list(TESTS)
SPECIMENS = ["serum", "plasma", "whole blood"]
QUARTER_START = {1: datetime(2024, 1, 1), 2: datetime(2024, 4, 1),
                 3: datetime(2024, 7, 1), 4: datetime(2024, 10, 1)}


def build_quarter(rng: random.Random, q: int) -> tuple[list[str], list[list[str]]]:
    rows = []
    for i in range(N):
        code = CODES[i % len(CODES)]
        unit, lo, hi = TESTS[code]
        value = f"{rng.uniform(lo, hi):.1f}"
        if q >= 3 and code == "HBA1C" and i % 10 == 1:
            unit, value = "mmol/mol", f"{rng.uniform(30, 80):.1f}"
        if q >= 3 and code == "CREAT" and i % 20 == 3:
            value = "<0.5"
        ts = QUARTER_START[q] + timedelta(days=rng.randrange(90), hours=rng.randrange(6, 18),
                                          minutes=rng.choice([0, 15, 30, 45]))
        collected = ts.strftime("%m/%d/%Y %H:%M") if q == 4 else ts.strftime("%Y-%m-%d %H:%M:%S")
        if q == 1:
            specimen = "" if i % 20 == 7 else SPECIMENS[i % 3]            # 95% filled
        else:
            specimen = "" if i % 5 in (1, 4) else SPECIMENS[i % 3]        # 60% filled
        age = "" if (q == 4 and i % 20 in (2, 9, 15)) else str(18 + (i * 13) % 71)  # Q4: 85%
        rows.append({
            "patient_id": f"P{rng.randrange(1, 5000):05d}",
            "encounter_id": f"E{q}{i:06d}",
            "collected_at": collected,
            "test_code": code,
            "value": value,
            "unit": unit,
            "specimen_type": specimen,
            "age_years": age,
            "ordering_provider": f"DR{(i * 11) % 37:03d}",
        })

    cols = {
        1: ["patient_id", "encounter_id", "collected_at", "test_code", "value", "unit",
            "specimen_type", "age_years"],
        2: ["patient_id", "encounter_id", "test_code", "collected_at", "value", "unit",
            "specimen_type", "age_years", "ordering_provider"],
        3: ["patient_id", "encounter_id", "test_code", "CollectedAt", "value", "unit",
            "specimen_type", "age_years", "ordering_provider"],
        4: ["patient_id", "encounter_id", "test_code", "CollectedAt", "value", "unit",
            "age_years", "ordering_provider"],
    }[q]
    out = []
    for r in rows:
        r["CollectedAt"] = r["collected_at"]
        out.append([r[c] for c in cols])
    return cols, out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    for q in (1, 2, 3, 4):
        cols, rows = build_quarter(rng, q)
        name = f"site_x_2024Q{q}.csv"
        with open(DATA / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        print(f"wrote {len(rows)} rows x {len(cols)} columns to data/{name}")


if __name__ == "__main__":
    main()
