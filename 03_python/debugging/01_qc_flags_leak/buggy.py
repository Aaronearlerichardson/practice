"""Record-level QC flags for incoming encounter records.

Each site's quarterly batch is validated record by record before it is
loaded into the bronze layer. A record with no flags is "clean".
"""
from __future__ import annotations

from collections import Counter

REQUIRED_FIELDS = ("record_id", "patient_id", "site_id", "encounter_date")
VALID_SEX = {"F", "M", "U"}
AGE_RANGE = (0, 120)          # years, inclusive
WEIGHT_RANGE = (0.3, 350.0)   # kg, inclusive


def collect_flags(record: dict, flags: tuple = ()) -> list:
    """Return QC flags for one record.

    `flags` lets a caller seed the list with flags raised upstream
    (e.g. by the file-level parser) so everything is reported together.
    """
    these_flags = list(flags)
    for field in REQUIRED_FIELDS:
        if record.get(field) in (None, ""):
            these_flags.append(f"missing:{field}")

    age = record.get("age")
    if age is not None and not (AGE_RANGE[0] <= age <= AGE_RANGE[1]):
        these_flags.append("implausible:age")

    weight = record.get("weight_kg")
    if weight is not None and not (WEIGHT_RANGE[0] <= weight <= WEIGHT_RANGE[1]):
        these_flags.append("implausible:weight_kg")

    sex = record.get("sex")
    if sex is not None and sex not in VALID_SEX:
        these_flags.append("invalid:sex")

    return these_flags


def validate_batch(records: list[dict]) -> dict[str, list[str]]:
    """Map record_id -> list of QC flags for every record in a batch."""
    results: dict[str, list[str]] = {}
    for i, record in enumerate(records):
        key = record.get("record_id") or f"<row {i}>"
        results[key] = collect_flags(record)
    return results


def summarize(results: dict[str, list[str]]) -> dict:
    """Batch-level QC summary for the site dashboard."""
    flag_counts = Counter(flag for flags in results.values() for flag in flags)
    n_clean = sum(1 for flags in results.values() if not flags)
    return {
        "n_records": len(results),
        "n_clean": n_clean,
        "clean_rate": round(n_clean / len(results), 3) if results else None,
        "flag_counts": dict(flag_counts),
    }
