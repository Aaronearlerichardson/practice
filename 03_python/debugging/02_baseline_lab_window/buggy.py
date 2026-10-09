"""Baseline lab selection for a cohort.

Protocol (from the study's statistical analysis plan):
  "The baseline value of a lab is the most recent result drawn within the
   30 days before the index date, inclusive of the index date itself.
   Day -30 is included; results after the index date are excluded."

Index dates are calendar dates (the date of the qualifying encounter).
Lab draw times are timestamps from the site's LIS, in site-local time.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

LOOKBACK_DAYS = 30


def in_baseline_window(drawn_at: datetime, index_date: date,
                       lookback_days: int = LOOKBACK_DAYS) -> bool:
    """True if a lab drawn at `drawn_at` falls in the baseline window."""
    window_end = datetime.combine(index_date, time.min)
    window_start = window_end - timedelta(days=lookback_days)
    return window_start <= drawn_at <= window_end


def baseline_labs(labs: list[dict], index_dates: dict[str, date],
                  lookback_days: int = LOOKBACK_DAYS) -> dict[tuple[str, str], dict]:
    """Pick the baseline result per (patient_id, test_code).

    labs: dicts with patient_id, test_code, drawn_at (datetime), value.
    index_dates: patient_id -> index date. Patients without one are skipped.
    Returns {(patient_id, test_code): lab_dict} using the latest draw in window.
    """
    best: dict[tuple[str, str], dict] = {}
    for lab in labs:
        index_date = index_dates.get(lab["patient_id"])
        if index_date is None:
            continue
        if not in_baseline_window(lab["drawn_at"], index_date, lookback_days):
            continue
        key = (lab["patient_id"], lab["test_code"])
        current = best.get(key)
        if current is None or lab["drawn_at"] > current["drawn_at"]:
            best[key] = lab
    return best


def baseline_coverage(labs: list[dict], index_dates: dict[str, date],
                      test_code: str) -> float:
    """Share of indexed patients that have a baseline value for `test_code`."""
    if not index_dates:
        return 0.0
    chosen = baseline_labs(labs, index_dates)
    have = {pid for (pid, code) in chosen if code == test_code}
    return len(have) / len(index_dates)
