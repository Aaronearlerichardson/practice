"""Task 01: join three differently shaped site deliveries into one standardized lab table.

Implement the functions below. Keep the names and signatures; the tests import them.
Use the standard library, pandas, or pyarrow, whichever you like.
"""
from __future__ import annotations

from pathlib import Path

STANDARD_COLUMNS = ["patient_id", "collected_date", "test_code", "value", "unit",
                    "site_id", "source_row", "comment"]
REJECT_COLUMNS = ["site_id", "source_row", "local_patient_id", "local_test_name",
                  "value", "collected_date", "reject_reason"]
LOCAL_FIELDS = ["local_patient_id", "local_test_name", "value", "unit",
                "collected_date", "comment"]


def load_mappings(path: str | Path) -> dict[str, dict]:
    """Read mappings.json: {site_id: {file, format, date_format, columns, test_map}}."""
    raise NotImplementedError


def load_crosswalk(path: str | Path) -> dict[tuple[str, str], str]:
    """Map (site_id, local_patient_id) -> patient_id.

    Keys are normalized: site_id stripped; local_patient_id stripped and uppercased.
    Duplicate rows that agree collapse to one entry. A key that maps to two different
    patient_ids raises ValueError.
    """
    raise NotImplementedError


def read_site(data_dir: str | Path, site_id: str, mapping: dict) -> list[dict[str, str]]:
    """Read one site's file (csv, tsv or parquet) and rename columns via mapping["columns"].

    Returns one dict per data row with exactly the keys LOCAL_FIELDS + ["source_row"].
    Every value is a str. A field the site does not send, or a null, becomes "".
    source_row is the 1-based data row number in the file (header excluded), as a str.
    Values are NOT trimmed or validated here.
    """
    raise NotImplementedError


def standardize_rows(site_id: str, rows: list[dict[str, str]], mapping: dict,
                     crosswalk: dict[tuple[str, str], str]) -> tuple[list[dict], list[dict]]:
    """Apply the rules in order. Return (good rows keyed by STANDARD_COLUMNS,
    reject rows keyed by REJECT_COLUMNS)."""
    raise NotImplementedError


def run(data_dir: str | Path, out_dir: str | Path) -> dict[str, int]:
    """Process every site in data_dir/mappings.json.

    Writes out_dir/labs_standardized.csv and out_dir/labs_rejects.csv (creating out_dir)
    and returns {"written": <good rows>, "rejected": <reject rows>}.
    """
    raise NotImplementedError


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    print(run(here / "data", here / "output"))
