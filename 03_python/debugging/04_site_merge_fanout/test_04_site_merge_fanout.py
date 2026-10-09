import numpy as np
import pandas as pd
import pytest

from buggy import enrich_encounters, volume_by_region


def make_sites():
    """Site reference after the 2026-07 refresh (type-2 history)."""
    return pd.DataFrame(
        [
            # S01: never changed
            ("S01", "Lakeside Medical", "Midwest", "Epic", "2024-01-01", None, True),
            # S02: migrated Cerner -> Epic in 2026-04
            ("S02", "Harbor Health", "Northeast", "Cerner", "2024-01-01", "2026-03-31", False),
            ("S02", "Harbor Health", "Northeast", "Epic", "2026-04-01", None, True),
            # S03: renamed twice
            ("S03", "Valley Clinic", "South", "Athena", "2023-06-01", "2025-01-31", False),
            ("S03", "Valley Clinic Group", "South", "Athena", "2025-02-01", "2026-05-31", False),
            ("S03", "Valley Health Partners", "South", "Athena", "2026-06-01", None, True),
            # S04: never changed
            ("S04", "Mesa Regional", "West", "Epic", "2024-01-01", None, True),
        ],
        columns=["site_id", "site_name", "region", "ehr_vendor",
                 "valid_from", "valid_to", "is_current"],
    )


def make_encounters(seed=42, n=1_000):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "encounter_id": [f"E{i:06d}" for i in range(n)],
        "patient_id": [f"P{p:05d}" for p in rng.integers(0, 400, n)],
        "site_id": rng.choice(["S01", "S02", "S03", "S04"], n),
    })


def test_row_count_is_preserved():
    enc = make_encounters()
    enriched = enrich_encounters(enc, make_sites())
    assert len(enriched) == len(enc)
    assert enriched["encounter_id"].is_unique


def test_uses_current_site_attributes():
    enc = make_encounters()
    enriched = enrich_encounters(enc, make_sites()).set_index("encounter_id")
    s02 = enriched[enriched["site_id"] == "S02"]
    s03 = enriched[enriched["site_id"] == "S03"]
    assert set(s02["ehr_vendor"]) == {"Epic"}
    assert set(s03["site_name"]) == {"Valley Health Partners"}


def test_volume_by_region_matches_raw_counts():
    enc = make_encounters()
    out = volume_by_region(enc, make_sites())
    assert out["n_encounters"].sum() == len(enc)
    by_region = dict(zip(out["region"], out["n_encounters"]))
    raw = enc["site_id"].map({"S01": "Midwest", "S02": "Northeast",
                              "S03": "South", "S04": "West"}).value_counts()
    assert by_region == raw.to_dict()
    assert list(out["ehr_vendor"]) == ["Epic", "Epic", "Athena", "Epic"]


def test_unknown_site_still_raises():
    enc = make_encounters()
    enc.loc[0, "site_id"] = "S99"
    with pytest.raises(ValueError, match="S99"):
        enrich_encounters(enc, make_sites())


def test_two_current_rows_for_a_site_is_an_error():
    """If onboarding ever leaves two current rows for one site, fail loudly
    (pandas raises MergeError, a ValueError subclass) instead of fanning out."""
    sites = make_sites()
    sites.loc[sites["site_id"] == "S03", "is_current"] = True
    with pytest.raises(pd.errors.MergeError):
        enrich_encounters(make_encounters(), sites)
