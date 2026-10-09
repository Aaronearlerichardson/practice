"""Enrich encounters with site attributes for the quarterly volume report.

`site_reference` is maintained by the site-onboarding team. Since the
2026-07 refresh it is a type-2 history table: one row per site per period,
with columns site_id, site_name, region, ehr_vendor, valid_from, valid_to,
is_current. Exactly one row per site should have is_current == True.
"""
from __future__ import annotations

import pandas as pd

SITE_COLUMNS = ["site_id", "site_name", "region", "ehr_vendor"]


def enrich_encounters(encounters: pd.DataFrame,
                      site_reference: pd.DataFrame) -> pd.DataFrame:
    """Attach site_name, region and ehr_vendor to every encounter row."""
    sites = site_reference[SITE_COLUMNS]
    enriched = encounters.merge(sites, on="site_id", how="left")
    missing = enriched["site_name"].isna()
    if missing.any():
        unknown = sorted(enriched.loc[missing, "site_id"].unique())
        raise ValueError(f"encounters reference unknown sites: {unknown}")
    return enriched


def load_site_reference(path) -> pd.DataFrame:
    """Read the reference extract published by the onboarding team (CSV)."""
    ref = pd.read_csv(path, dtype={"site_id": str}, parse_dates=["valid_from", "valid_to"])
    ref["is_current"] = ref["is_current"].astype(str).str.lower().eq("true")
    return ref


def volume_by_region(encounters: pd.DataFrame,
                     site_reference: pd.DataFrame) -> pd.DataFrame:
    """Encounter and distinct-patient counts per region and EHR vendor."""
    enriched = enrich_encounters(encounters, site_reference)
    out = (
        enriched.groupby(["region", "ehr_vendor"], as_index=False)
        .agg(n_encounters=("encounter_id", "size"),
             n_patients=("patient_id", "nunique"))
        .sort_values(["region", "ehr_vendor"], ignore_index=True)
    )
    return out
