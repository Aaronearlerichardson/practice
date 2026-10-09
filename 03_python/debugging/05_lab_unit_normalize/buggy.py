"""Normalize lab results to canonical units and flag implausible values.

Input columns: lab_id, test_code, unit, value (float, may be missing).
Adds:
  value_std   value in the canonical unit (NaN if unknown unit or no value)
  unit_std    canonical unit (missing if the (test, unit) pair is unknown)
  plausible   True only if value_std is within the plausibility range
  qc_reason   "" | "unknown_unit" | "missing_value" | "out_of_range"
              (checked in that order; the first that applies wins)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# (test_code, source unit) -> (canonical unit, multiplier)
CONVERSIONS = {
    ("glucose", "mg/dL"): ("mmol/L", 1 / 18.016),
    ("glucose", "mmol/L"): ("mmol/L", 1.0),
    ("creatinine", "mg/dL"): ("umol/L", 88.42),
    ("creatinine", "umol/L"): ("umol/L", 1.0),
    ("cholesterol", "mg/dL"): ("mmol/L", 1 / 38.67),
    ("cholesterol", "mmol/L"): ("mmol/L", 1.0),
    ("hemoglobin", "g/dL"): ("g/dL", 1.0),
    ("hemoglobin", "g/L"): ("g/dL", 0.1),
    ("hba1c", "%"): ("%", 1.0),
}

# Plausibility range in the canonical unit, inclusive.
PLAUSIBLE_RANGE = {
    "glucose": (1.0, 45.0),
    "creatinine": (10.0, 2500.0),
    "cholesterol": (1.0, 20.0),
    "hemoglobin": (3.0, 25.0),
    "hba1c": (3.0, 20.0),
}


def normalize_labs(labs: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `labs` with value_std, unit_std, plausible, qc_reason."""
    out = labs.copy()
    out["value_std"] = np.nan
    out["unit_std"] = None
    out["plausible"] = False
    out["qc_reason"] = ""

    for idx, row in labs.iterrows():
        test = str(row["test_code"]).strip().lower()
        unit = str(row["unit"]).strip()
        conversion = CONVERSIONS.get((test, unit))
        if conversion is None:
            out.at[idx, "qc_reason"] = "unknown_unit"
            continue
        unit_std, factor = conversion
        out.at[idx, "unit_std"] = unit_std
        if pd.isna(row["value"]):
            out.at[idx, "qc_reason"] = "missing_value"
            continue
        value_std = float(row["value"]) * factor
        out.at[idx, "value_std"] = value_std
        low, high = PLAUSIBLE_RANGE[test]
        if low <= value_std <= high:
            out.at[idx, "plausible"] = True
        else:
            out.at[idx, "qc_reason"] = "out_of_range"
    return out


def plausibility_summary(normalized: pd.DataFrame) -> pd.DataFrame:
    """Per-test fill rate and plausibility rate for the site QC report."""
    g = normalized.assign(test=normalized["test_code"].str.strip().str.lower())
    return (
        g.groupby("test")
        .agg(n=("lab_id", "size"),
             fill_rate=("value_std", lambda s: s.notna().mean()),
             plausible_rate=("plausible", "mean"))
        .round(4)
    )
