"""Tests for task 04. Run: python -m pytest 03_python/data_tasks/04_schema_drift -q"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE))
sys.modules.pop("solution", None)

from solution import (  # noqa: E402
    ColumnInfo, Drift, compare, drift_report, infer_schema, infer_type, normalize_name,
)

Q = [DATA / f"site_x_2024Q{i}.csv" for i in (1, 2, 3, 4)]


def kinds(drifts):
    return [(d.kind, d.column) for d in drifts]


def write_csv(path: Path, header, rows) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def col(name, type_="string", fmt=None, fill=1.0, cats=None):
    return ColumnInfo(name, type_, fmt, fill, None if cats is None else frozenset(cats))


def schema(*cols):
    return {c.name: c for c in cols}


# ---- type inference ----------------------------------------------------------

@pytest.mark.parametrize("values,expected", [
    (["1", "2", "-3", ""], ("int", None)),
    (["1", "2.5"], ("float", None)),
    (["1e3", ".5", "-2."], ("float", None)),
    (["nan", "1.0"], ("string", None)),           # 'nan' is not a number here
    (["<0.5", "1.2"], ("string", None)),
    (["2024-01-02", "2024-12-31"], ("date", "%Y-%m-%d")),
    (["01/02/2024", "12/31/2024"], ("date", "%m/%d/%Y")),
    (["2024-02-30"], ("string", None)),           # not a real date
    (["2024-01-02 08:00:00"], ("datetime", "%Y-%m-%d %H:%M:%S")),
    (["2024-01-02T08:00:00"], ("datetime", "%Y-%m-%dT%H:%M:%S")),
    (["01/02/2024 08:00"], ("datetime", "%m/%d/%Y %H:%M")),
    (["2024-01-02", "2024-01-02 08:00:00"], ("string", None)),   # mixed date/datetime
    (["2024-01-02", "01/02/2024"], ("string", None)),            # mixed formats
    (["20240102"], ("int", None)),
    (["", "  "], ("string", None)),               # no non-empty values
    ([" 7 ", "8"], ("int", None)),                # values are stripped
    (["P001", "P002"], ("string", None)),
])
def test_infer_type(values, expected):
    assert infer_type(values) == expected


def test_normalize_name():
    assert normalize_name("collected_at") == normalize_name("CollectedAt") == "collectedat"
    assert normalize_name("Collected At (UTC)") == "collectedatutc"
    assert normalize_name("HbA1c_2") == "hba1c2"


def test_infer_schema_q1():
    s = infer_schema(Q[0])
    assert list(s) == ["patient_id", "encounter_id", "collected_at", "test_code", "value",
                       "unit", "specimen_type", "age_years"]
    assert s["collected_at"].type == "datetime"
    assert s["collected_at"].fmt == "%Y-%m-%d %H:%M:%S"
    assert s["value"].type == "float"
    assert s["age_years"].type == "int"
    assert s["patient_id"].type == "string"
    assert s["specimen_type"].fill_rate == pytest.approx(0.95)
    assert s["specimen_type"].categories == frozenset({"serum", "plasma", "whole blood"})
    assert s["unit"].categories == frozenset({"mg/dL", "%", "mmol/L", "g/dL"})
    assert s["patient_id"].categories is None      # too many distinct values
    assert s["value"].fmt is None


def test_infer_schema_q4():
    s = infer_schema(Q[3])
    assert s["CollectedAt"].type == "datetime"
    assert s["CollectedAt"].fmt == "%m/%d/%Y %H:%M"
    assert s["value"].type == "string"
    assert s["age_years"].fill_rate == pytest.approx(0.85)
    assert "specimen_type" not in s


def test_infer_schema_fill_rate_and_categories(tmp_path):
    p = write_csv(tmp_path / "t.csv", ["a", "b"],
                  [["x", "1"], [" ", "2"], ["y", ""], ["x", "3"]])
    s = infer_schema(p)
    assert s["a"].fill_rate == pytest.approx(0.75)
    assert s["a"].categories == frozenset({"x", "y"})
    assert s["b"].fill_rate == pytest.approx(0.75)
    assert s["b"].type == "int"


# ---- the planted drift ---------------------------------------------------------

@pytest.fixture(scope="module")
def schemas():
    return [infer_schema(p) for p in Q]


def test_q1_to_q2(schemas):
    d = compare(schemas[0], schemas[1])
    assert kinds(d) == [("added", "ordering_provider"), ("fill_rate_drop", "specimen_type")]


def test_q2_to_q3(schemas):
    d = compare(schemas[1], schemas[2])
    assert kinds(d) == [("new_values", "unit"), ("renamed", "CollectedAt"),
                        ("type_changed", "value")]
    by_kind = {x.kind: x for x in d}
    assert "mmol/mol" in by_kind["new_values"].detail
    assert "collected_at" in by_kind["renamed"].detail


def test_q3_to_q4(schemas):
    d = compare(schemas[2], schemas[3])
    assert kinds(d) == [("date_format_changed", "CollectedAt"), ("removed", "specimen_type")]


def test_drift_objects_are_drift_dataclass(schemas):
    d = compare(schemas[0], schemas[1])
    assert all(isinstance(x, Drift) for x in d)


def test_same_file_has_no_drift(schemas):
    for s in schemas:
        assert compare(s, s) == []


def test_pure_reorder_is_not_drift(tmp_path):
    a = write_csv(tmp_path / "a.csv", ["x", "y", "z"], [["1", "a", "2024-01-01"]] * 5)
    b = write_csv(tmp_path / "b.csv", ["z", "x", "y"], [["2024-01-01", "1", "a"]] * 5)
    assert compare(infer_schema(a), infer_schema(b)) == []


# ---- compare rules on hand-built schemas ----------------------------------------

def test_rename_with_type_change_reports_both():
    prev = schema(col("collected_at", "date", "%Y-%m-%d"))
    curr = schema(col("Collected-At", "datetime", "%Y-%m-%d %H:%M:%S"))
    assert kinds(compare(prev, curr)) == [("renamed", "Collected-At"),
                                          ("type_changed", "Collected-At")]


def test_ambiguous_rename_is_added_and_removed():
    prev = schema(col("collected_at"))
    curr = schema(col("CollectedAt"), col("collected-at"))
    assert kinds(compare(prev, curr)) == [("added", "CollectedAt"), ("added", "collected-at"),
                                          ("removed", "collected_at")]


def test_type_change_suppresses_format_change():
    prev = schema(col("d", "date", "%Y-%m-%d"))
    curr = schema(col("d", "string", None))
    assert kinds(compare(prev, curr)) == [("type_changed", "d")]


def test_int_to_float_is_a_type_change():
    assert kinds(compare(schema(col("n", "int")), schema(col("n", "float")))) == [
        ("type_changed", "n")]


def test_date_format_change_same_type():
    prev = schema(col("d", "date", "%Y-%m-%d"))
    curr = schema(col("d", "date", "%m/%d/%Y"))
    assert kinds(compare(prev, curr)) == [("date_format_changed", "d")]


@pytest.mark.parametrize("before,after,reported", [
    (1.0, 0.85, False),
    (0.95, 0.6, True),
    (0.9, 0.7, False),     # exactly 20 points is not "more than 20"
    (0.9, 0.69, True),
    (0.5, 0.9, False),     # a rise is never drift
])
def test_fill_rate_threshold(before, after, reported):
    d = compare(schema(col("c", fill=before)), schema(col("c", fill=after)))
    assert kinds(d) == ([("fill_rate_drop", "c")] if reported else [])


def test_new_values_only_when_both_sides_categorical():
    assert kinds(compare(schema(col("u", cats={"a"})), schema(col("u", cats={"a", "b"})))) == [
        ("new_values", "u")]
    assert compare(schema(col("u", cats={"a", "b"})), schema(col("u", cats={"a"}))) == []
    assert compare(schema(col("u", cats=None)), schema(col("u", cats={"a"}))) == []
    assert compare(schema(col("u", cats={"a"})), schema(col("u", cats=None))) == []


def test_sorted_by_kind_then_column():
    prev = schema(col("b"), col("a"), col("z", "int"))
    curr = schema(col("z", "float"), col("c"), col("d"))
    assert kinds(compare(prev, curr)) == [("added", "c"), ("added", "d"), ("removed", "a"),
                                          ("removed", "b"), ("type_changed", "z")]


# ---- markdown report ------------------------------------------------------------

def test_drift_report_structure():
    md = drift_report(Q)
    lines = md.splitlines()
    assert lines[0] == "# Schema drift report"
    headings = [ln for ln in lines if ln.startswith("## ")]
    assert headings == [
        "## site_x_2024Q1.csv -> site_x_2024Q2.csv",
        "## site_x_2024Q2.csv -> site_x_2024Q3.csv",
        "## site_x_2024Q3.csv -> site_x_2024Q4.csv",
    ]
    assert md.count("| kind | column | detail |") == 3
    rows = [ln for ln in lines if ln.startswith("| ") and not ln.startswith("| kind ")]
    assert len(rows) == 2 + 3 + 2
    assert any(ln.startswith("| added | ordering_provider |") for ln in rows)
    assert any(ln.startswith("| renamed | CollectedAt |") for ln in rows)
    assert any(ln.startswith("| removed | specimen_type |") for ln in rows)
    assert not any("age_years" in ln for ln in rows)
    assert not any("test_code" in ln for ln in rows)


def test_drift_report_no_drift(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    shutil.copy(Q[0], a)
    shutil.copy(Q[0], b)
    md = drift_report([a, b])
    assert "## a.csv -> b.csv" in md
    assert "No drift." in md
    assert "| kind |" not in md


def test_drift_report_needs_two_files():
    with pytest.raises(ValueError):
        drift_report([Q[0]])
