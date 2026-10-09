"""Generate lab rows for task 03.

    python gen_data.py                 # data/labs_sample.csv (small, committed)
    python gen_data.py --size-mb 2000  # data/big/labs_big.csv (gitignored), ~2 GB

Fixed seed: same arguments give byte-identical output.
All data is synthetic. No real patients.
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEED = 303
HEADER = "row_id,site_id,patient_id,test_code,collected_date,value,unit\n"

# test_code: (low, high, unit). Same table as PLAUSIBLE in solution.py.
TESTS = {
    "GLU": (10.0, 1000.0, "mg/dL"),
    "HBA1C": (2.0, 20.0, "%"),
    "K": (1.5, 10.0, "mmol/L"),
    "NA": (100.0, 180.0, "mmol/L"),
    "HGB": (2.0, 25.0, "g/dL"),
    "CREAT": (0.1, 20.0, "mg/dL"),
}
CODES = list(TESTS)
SITES = [f"S{i:02d}" for i in range(1, 13)]
NON_NUMERIC = ["", "NaN", "pending", "<5", "see note"]
D0 = date(2024, 1, 1)

# Handcrafted rows that open the sample file: (site_id, test_code, value)
HANDCRAFTED = [
    ("S01", "GLU", "100"),
    ("S01", "GLU", "1e2"),
    ("S01", " glu", "130"),
    ("S01", "GLU", "NaN"),
    ("S01", "GLU", "1000"),
    ("S01", "GLU", "1000.01"),
    ("S01", "K", " 4.5 "),
    ("S01", "K", "-1"),
    ("S01", "K", ""),
    ("S01", "K", "inf"),
    (" S02", "HBA1C", "6.5"),
    ("S02", "hba1c", "7.5"),
    ("S02", "XYZ", "5"),
    ("S03", "CREAT", "abc"),
    ("S03", "CREAT", "50"),
    ("S01", "GLU", "10"),
]


def _row(rng: random.Random, row_id: int, counts: dict[str, int]) -> str:
    site = rng.choice(SITES)
    code = rng.choice(CODES)
    lo, hi, unit = TESTS[code]
    r = rng.random()
    if r < 0.005:
        code_out, value = "LDL", f"{rng.uniform(40, 190):.0f}"
        counts["unknown_test"] += 1
    elif r < 0.015:
        code_out, value = code, rng.choice(NON_NUMERIC)
        counts["non_numeric"] += 1
    elif r < 0.025:
        code_out = code
        value = f"{hi * 1.5 + 1:.2f}" if rng.random() < 0.5 else f"{-rng.uniform(0.5, 5):.2f}"
        counts["implausible"] += 1
    else:
        code_out = code
        value = f"{rng.uniform(lo + 0.05 * (hi - lo), lo + 0.6 * (hi - lo)):.2f}"
        counts["valid"] += 1
    s = rng.random()
    if s < 0.03:
        code_out = code_out.lower()
    elif s < 0.05:
        code_out = f" {code_out} "
    d = D0 + timedelta(days=rng.randrange(366))
    return (f"{row_id},{site},P{rng.randrange(1, 200_000):06d},{code_out},"
            f"{d.isoformat()},{value},{unit}\n")


def write_big(path: str | Path, size_mb: float, seed: int = SEED) -> dict:
    """Write rows until the file reaches size_mb megabytes (10**6 bytes).

    Returns {"rows", "bytes", "valid", "invalid", "by_reason"} so a test can reconcile.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    target = int(size_mb * 1_000_000)
    counts = {"valid": 0, "unknown_test": 0, "non_numeric": 0, "implausible": 0}
    n = 0
    written = len(HEADER)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(HEADER)
        buf = []
        while written < target:
            n += 1
            line = _row(rng, n, counts)
            written += len(line)
            buf.append(line)
            if len(buf) >= 10_000:
                f.write("".join(buf))
                buf.clear()
        f.write("".join(buf))
    invalid = counts["unknown_test"] + counts["non_numeric"] + counts["implausible"]
    return {"rows": n, "bytes": written, "valid": counts["valid"], "invalid": invalid,
            "by_reason": {k: v for k, v in counts.items() if k != "valid"}}


def write_sample(path: str | Path, n_random: int = 284, seed: int = SEED) -> int:
    """Handcrafted rows first, then n_random generated rows. Returns total rows."""
    rng = random.Random(seed)
    counts = {"valid": 0, "unknown_test": 0, "non_numeric": 0, "implausible": 0}
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(HEADER)
        for i, (site, code, value) in enumerate(HANDCRAFTED, start=1):
            unit = TESTS.get(code.strip().upper(), (0, 0, "U"))[2]
            f.write(f'{i},"{site}",P{i:06d},"{code}",2024-02-{i:02d},"{value}",{unit}\n')
        for j in range(n_random):
            f.write(_row(rng, len(HANDCRAFTED) + 1 + j, counts))
    return len(HANDCRAFTED) + n_random


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--size-mb", type=float, default=None,
                    help="write data/big/labs_big.csv of about this many MB instead of the sample")
    args = ap.parse_args()
    if args.size_mb is None:
        DATA.mkdir(parents=True, exist_ok=True)
        n = write_sample(DATA / "labs_sample.csv")
        print(f"wrote {n} rows to data/labs_sample.csv")
    else:
        out = DATA / "big" / "labs_big.csv"
        stats = write_big(out, args.size_mb)
        print(f"wrote {stats['rows']:,} rows ({stats['bytes'] / 1e6:,.1f} MB) to {out}")
        print(f"planted invalid: {stats['invalid']:,} {stats['by_reason']}")


if __name__ == "__main__":
    main()
