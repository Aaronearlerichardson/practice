"""Per-test summary of a site's raw lab extract (bronze-layer profiling).

Sites deliver one delimited file per quarter with columns:
  patient_id, site_id, test_code, value, unit, drawn_at, result_status
`value` is text: it may be blank (missing) or non-numeric ("<0.5", "see note").
Rows with result_status == "cancelled" are ignored.

The summary feeds the fill-rate / plausibility dashboard.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path


def _new_stats() -> dict:
    return {"n": 0, "n_missing": 0, "n_nonnumeric": 0,
            "sum": 0.0, "min": math.inf, "max": -math.inf}


def summarize_lab_extract(path: Path | str, delimiter: str = ",") -> dict[str, dict]:
    """Return {test_code: {n, n_missing, n_nonnumeric, n_numeric, mean, min, max}}."""
    with open(path, newline="", encoding="utf-8") as f:
        lines = f.read().splitlines()

    reader = csv.reader(lines, delimiter=delimiter)
    header = next(reader)
    col = {name: i for i, name in enumerate(header)}
    i_test, i_value, i_status = col["test_code"], col["value"], col["result_status"]

    stats: dict[str, dict] = {}
    for row in reader:
        if not row or row[i_status] == "cancelled":
            continue
        s = stats.setdefault(row[i_test], _new_stats())
        s["n"] += 1
        raw = row[i_value].strip()
        if raw == "":
            s["n_missing"] += 1
            continue
        try:
            value = float(raw)
        except ValueError:
            s["n_nonnumeric"] += 1
            continue
        s["sum"] += value
        s["min"] = min(s["min"], value)
        s["max"] = max(s["max"], value)

    return {test: _finalize(s) for test, s in sorted(stats.items())}


def _finalize(s: dict) -> dict:
    n_numeric = s["n"] - s["n_missing"] - s["n_nonnumeric"]
    return {
        "n": s["n"],
        "n_missing": s["n_missing"],
        "n_nonnumeric": s["n_nonnumeric"],
        "n_numeric": n_numeric,
        "fill_rate": round(n_numeric / s["n"], 4) if s["n"] else None,
        "mean": round(s["sum"] / n_numeric, 4) if n_numeric else None,
        "min": s["min"] if n_numeric else None,
        "max": s["max"] if n_numeric else None,
    }
