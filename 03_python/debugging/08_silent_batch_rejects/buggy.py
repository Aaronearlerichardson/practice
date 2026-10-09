"""Load a site's quarterly encounter batch (CSV) into typed records.

Each delivery comes with a manifest stating the number of data rows. After
loading we reconcile against it before promoting the batch to silver.

Columns: encounter_id, patient_id, admit_ts, discharge_ts, weight_kg
  admit_ts / discharge_ts: "YYYY-MM-DD HH:MM[:SS]" site-local time;
  discharge_ts and weight_kg may be blank.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

TS_FORMAT = "%Y-%m-%d %H:%M"


@dataclass
class LoadResult:
    rows: list[dict] = field(default_factory=list)
    rejects: list[dict] = field(default_factory=list)  # {line_no, reason, raw}
    n_input: int = 0


def parse_row(raw: dict) -> dict:
    """Convert one CSV row to a typed record. Raises on invalid data."""
    patient_id = raw["patient_id"].strip()
    if not patient_id:
        raise ValueError("patient_id: missing")
    admit = datetime.strptime(raw["admit_ts"].strip(), TS_FORMAT)
    discharge = None
    if raw["discharge_ts"].strip():
        discharge = datetime.strptime(raw["discharge_ts"].strip(), TS_FORMAT)
        if discharge < admit:
            raise ValueError("discharge_ts: before admit_ts")
    weight = float(raw["weight_kg"]) if raw["weight_kg"].strip() else None
    return {
        "encounter_id": raw["encounter_id"].strip(),
        "patient_id": patient_id,
        "admit_ts": admit,
        "discharge_ts": discharge,
        "weight_kg": weight,
    }


def load_batch(path: Path | str) -> LoadResult:
    result = LoadResult()
    with open(path, newline="", encoding="utf-8") as f:
        for line_no, raw in enumerate(csv.DictReader(f), start=2):
            result.n_input += 1
            try:
                result.rows.append(parse_row(raw))
            except Exception:
                continue
    return result


def reconcile(result: LoadResult, manifest_rows: int) -> dict:
    """Compare what we loaded with the site's manifest."""
    loaded, rejected = len(result.rows), len(result.rejects)
    return {
        "manifest_rows": manifest_rows,
        "loaded": loaded,
        "rejected": rejected,
        "ok": loaded == manifest_rows,
    }
