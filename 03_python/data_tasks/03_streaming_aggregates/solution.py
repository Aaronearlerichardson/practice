"""Task 03: one-pass, constant-memory per-(site, test) stats with a streamed rejects file.

Implement the functions below. Keep the names and signatures; the tests import them.
"""
from __future__ import annotations

from pathlib import Path

# Inclusive plausibility ranges. A test_code not in this table is unknown.
PLAUSIBLE: dict[str, tuple[float, float]] = {
    "GLU": (10.0, 1000.0),
    "HBA1C": (2.0, 20.0),
    "K": (1.5, 10.0),
    "NA": (100.0, 180.0),
    "HGB": (2.0, 25.0),
    "CREAT": (0.1, 20.0),
}
INPUT_COLUMNS = ["row_id", "site_id", "patient_id", "test_code", "collected_date", "value", "unit"]
SUMMARY_COLUMNS = ["site_id", "test_code", "count", "invalid_count", "mean", "min", "max"]
REJECT_COLUMNS = INPUT_COLUMNS + ["reason"]


def classify(test_code: str, value: str) -> tuple[float | None, str | None]:
    """Return (parsed value, None) for a valid row, or (None, reason) for an invalid one.

    test_code is already normalized (stripped, uppercased); value is the raw text.
    Reasons, checked in this order: 'unknown_test', 'non_numeric', 'implausible'.
    """
    raise NotImplementedError


def summarize(in_path: str | Path, summary_path: str | Path,
              rejects_path: str | Path) -> dict[str, int]:
    """Read in_path once, in constant memory. Write the summary CSV and the rejects CSV.

    Returns {"rows_read": n, "valid": n, "invalid": n}.
    """
    raise NotImplementedError


if __name__ == "__main__":
    import sys
    here = Path(__file__).resolve().parent
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "data" / "labs_sample.csv"
    out = here / "output"
    out.mkdir(exist_ok=True)
    print(summarize(src, out / "summary.csv", out / "rejects.csv"))
