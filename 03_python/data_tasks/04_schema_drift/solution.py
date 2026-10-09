"""Task 04: infer a schema per quarterly file and report drift between consecutive quarters.

Implement the functions below. Keep the names and signatures; the tests import them.
The dataclasses and constants are part of the spec: use them as given.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y"]
DATETIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M"]
MAX_CATEGORIES = 20
FILL_DROP_THRESHOLD = 0.20


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str                          # int | float | date | datetime | string
    fmt: str | None                    # strptime format for date/datetime, else None
    fill_rate: float                   # non-empty / rows, rounded to 4 decimals
    categories: frozenset[str] | None  # distinct non-empty values if <= MAX_CATEGORIES, else None


@dataclass(frozen=True)
class Drift:
    kind: str     # added | removed | renamed | type_changed | date_format_changed
                  # | fill_rate_drop | new_values
    column: str   # the current name (the old name for 'removed')
    detail: str   # free text for humans, e.g. "float -> string"


def normalize_name(name: str) -> str:
    """Lowercase and drop every character that is not a-z or 0-9."""
    raise NotImplementedError


def infer_type(values: list[str]) -> tuple[str, str | None]:
    """Narrowest type that fits every non-empty (stripped) value. Returns (type, fmt)."""
    raise NotImplementedError


def infer_schema(path: str | Path) -> dict[str, ColumnInfo]:
    """Profile every column of a CSV. Keys are column names, in file order."""
    raise NotImplementedError


def compare(prev: dict[str, ColumnInfo], curr: dict[str, ColumnInfo]) -> list[Drift]:
    """Drift from prev to curr, sorted by (kind, column). Column order is ignored."""
    raise NotImplementedError


def drift_report(paths: list[str | Path]) -> str:
    """Markdown report comparing each consecutive pair of files (see prompt.md for format)."""
    raise NotImplementedError


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    print(drift_report(sorted((here / "data").glob("site_x_2024Q*.csv"))))
