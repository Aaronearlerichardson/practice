from datetime import date, datetime

import pytest

from buggy import baseline_coverage, baseline_labs, in_baseline_window

INDEX = date(2026, 3, 31)  # day -30 is 2026-03-01


@pytest.mark.parametrize("drawn_at, expected", [
    (datetime(2026, 3, 31, 0, 0), True),        # index day, midnight
    (datetime(2026, 3, 31, 14, 30), True),      # index day, afternoon
    (datetime(2026, 3, 31, 23, 59, 59), True),  # index day, last second
    (datetime(2026, 4, 1, 0, 0), False),        # day +1
    (datetime(2026, 3, 1, 0, 0), True),         # day -30, midnight
    (datetime(2026, 3, 1, 22, 15), True),       # day -30, late evening
    (datetime(2026, 2, 28, 23, 59), False),     # day -31
])
def test_window_edges(drawn_at, expected):
    assert in_baseline_window(drawn_at, INDEX) is expected


def make_labs():
    return [
        # P1: HbA1c three weeks before, and again the morning of the index visit
        {"patient_id": "P1", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 10, 9, 5), "value": 7.9},
        {"patient_id": "P1", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 31, 10, 40), "value": 8.4},
        # P1: one day after index, must not be used
        {"patient_id": "P1", "test_code": "HBA1C", "drawn_at": datetime(2026, 4, 1, 8, 0), "value": 8.1},
        # P2: only lab is on the index day (afternoon)
        {"patient_id": "P2", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 31, 16, 20), "value": 6.2},
        # P3: only lab is on day -30 (evening)
        {"patient_id": "P3", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 1, 19, 0), "value": 9.0},
        # P4: too early (day -31)
        {"patient_id": "P4", "test_code": "HBA1C", "drawn_at": datetime(2026, 2, 28, 12, 0), "value": 5.6},
        # P9 has no index date
        {"patient_id": "P9", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 20, 12, 0), "value": 5.1},
    ]


INDEX_DATES = {"P1": INDEX, "P2": INDEX, "P3": INDEX, "P4": INDEX}


def test_baseline_uses_same_day_draw():
    chosen = baseline_labs(make_labs(), INDEX_DATES)
    assert chosen[("P1", "HBA1C")]["value"] == 8.4


def test_baseline_selection_all_patients():
    chosen = baseline_labs(make_labs(), INDEX_DATES)
    assert {k: v["value"] for k, v in chosen.items()} == {
        ("P1", "HBA1C"): 8.4,
        ("P2", "HBA1C"): 6.2,
        ("P3", "HBA1C"): 9.0,
    }


def test_coverage():
    assert baseline_coverage(make_labs(), INDEX_DATES, "HBA1C") == 0.75
