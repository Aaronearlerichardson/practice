"""De-duplicate encounter rows across overlapping quarterly deliveries.

Sites re-send the tail of the previous quarter in each new batch, and some
send the same encounter twice inside one file after a re-extract. Before the
bronze -> silver step we keep the FIRST occurrence of each encounter (the
earliest delivery wins) and preserve the original row order.
"""
from __future__ import annotations

import csv
from pathlib import Path

KEY_FIELDS = ("site_id", "patient_id", "encounter_id")


def encounter_key(row: dict, key_fields: tuple[str, ...] = KEY_FIELDS) -> tuple:
    """Natural key of an encounter; whitespace and case are not significant."""
    return tuple(str(row[f]).strip().upper() for f in key_fields)


def dedupe_encounters(rows: list[dict],
                      key_fields: tuple[str, ...] = KEY_FIELDS) -> list[dict]:
    """Return rows with duplicates removed, keeping first occurrence, in order."""
    seen = []
    kept = []
    for row in rows:
        key = encounter_key(row, key_fields)
        if key not in seen:
            seen.append(key)
            kept.append(row)
    return kept


def dedupe_report(rows: list[dict]) -> dict:
    """Counts for the load log."""
    kept = dedupe_encounters(rows)
    return {
        "n_input": len(rows),
        "n_kept": len(kept),
        "n_duplicates_dropped": len(rows) - len(kept),
    }


def read_batches(paths: list[Path]) -> list[dict]:
    """Concatenate CSV batches in delivery order, tagging each row's source."""
    rows: list[dict] = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                row["source_file"] = Path(path).name
                rows.append(row)
    return rows
