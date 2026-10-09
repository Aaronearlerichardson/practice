"""Generate quarterly lab deliveries (with a resend, a correction and a broken file) for task 02.

Fixed seed: `python gen_data.py` rewrites data/ byte-identically.
All data is synthetic. No real patients.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEED = 202
HEADER = ["patient_id", "test_code", "collected_date", "value", "unit"]

TESTS = {
    "GLU": ("mg/dL", 70, 180, 0),
    "HBA1C": ("%", 4.8, 9.5, 1),
    "K": ("mmol/L", 3.4, 5.2, 1),
    "CREAT": ("mg/dL", 0.6, 1.4, 2),
}


def _rows(rng: random.Random, n: int, start: date, days: int, prefix: str) -> list[list[str]]:
    rows = []
    for _ in range(n):
        code = rng.choice(list(TESTS))
        unit, lo, hi, dec = TESTS[code]
        d = start + timedelta(days=rng.randrange(days))
        rows.append([f"{prefix}{rng.randrange(1, 25):04d}", code, d.isoformat(),
                     f"{rng.uniform(lo, hi):.{dec}f}", unit])
    return rows


def _write(name: str, rows: list[list[str]]) -> None:
    with open(DATA / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def build() -> dict[str, list[list[str]]]:
    rng = random.Random(SEED)
    q1 = _rows(rng, 60, date(2024, 1, 1), 90, "P")
    q1[10][2] = "2024-03-31"            # last day of Q1: valid
    q1[11][2] = "2024-01-01"            # first day of Q1: valid

    corrected = [list(r) for r in q1]
    # three corrected results
    corrected[4] = [q1[4][0], "HBA1C", q1[4][2], "6.1", "%"]
    corrected[5] = [q1[5][0], "GLU", q1[5][2], "142", "mg/dL"]
    corrected[20] = [q1[20][0], "K", q1[20][2], "4.9", "mmol/L"]
    del corrected[30]                   # two rows withdrawn by the site
    del corrected[30]
    corrected.append(["P0024", "CREAT", "2024-02-29", "1.07", "mg/dL"])  # one late row

    broken = [list(r) for r in corrected]
    broken[39][2] = "2024-04-01"        # line 41 of the file: first day of Q2, out of quarter

    q2 = _rows(rng, 55, date(2024, 4, 1), 91, "P")
    q2[0][2] = "2024-04-01"
    q2[1][2] = "2024-06-30"

    s02 = _rows(rng, 40, date(2024, 1, 1), 91, "Q")
    return {
        "s01_2024Q1.csv": q1,
        "s01_2024Q1_resend.csv": q1,
        "s01_2024Q1_corrected.csv": corrected,
        "s01_2024Q1_broken.csv": broken,
        "s01_2024Q2.csv": q2,
        "s02_2024Q1.csv": s02,
    }


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name, rows in build().items():
        _write(name, rows)
        print(f"wrote {len(rows):3d} rows to data/{name}")


if __name__ == "__main__":
    main()
