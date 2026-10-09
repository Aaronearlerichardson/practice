"""Generate the synthetic three-site lab delivery for task 01.

Fixed seed: `python gen_data.py` rewrites data/ byte-identically.
All data is synthetic. No real patients.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEED = 101

# code: (unit, low, high, decimals)
TESTS = {
    "GLU": ("mg/dL", 70, 180, 0),
    "HBA1C": ("%", 4.8, 9.5, 1),
    "K": ("mmol/L", 3.4, 5.2, 1),
    "CREAT": ("mg/dL", 0.6, 1.4, 2),
    "HGB": ("g/dL", 11.0, 16.5, 1),
}

SITE_TEST_NAMES = {
    "site_a": {"GLU": "Glucose, Fasting", "HBA1C": "Hemoglobin A1c", "K": "Potassium",
               "CREAT": "Creatinine", "HGB": "Hemoglobin"},
    "site_b": {"GLU": "GLUC", "HBA1C": "A1C", "K": "K+", "CREAT": "CREA", "HGB": "HGB"},
    "site_c": {"GLU": "glucose_serum", "HBA1C": "hba1c_pct", "K": "potassium_serum",
               "CREAT": "creatinine_serum", "HGB": "hemoglobin_bld"},
}

MAPPINGS = {
    "site_a": {
        "file": "site_a_labs.csv",
        "format": "csv",
        "date_format": "%Y-%m-%d",
        "columns": {"MRN": "local_patient_id", "TestName": "local_test_name",
                    "ResultValue": "value", "Units": "unit",
                    "CollectedDate": "collected_date", "Comment": "comment"},
    },
    "site_b": {
        "file": "site_b_labs.tsv",
        "format": "tsv",
        "date_format": "%m/%d/%Y",
        "columns": {"patient_ref": "local_patient_id", "test": "local_test_name",
                    "value": "value", "unit": "unit",
                    "date_collected": "collected_date", "notes": "comment"},
    },
    "site_c": {
        "file": "site_c_labs.parquet",
        "format": "parquet",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "columns": {"pid": "local_patient_id", "lab_name": "local_test_name",
                    "result": "value", "result_unit": "unit",
                    "collection_ts": "collected_date"},
    },
}

Q1_START = date(2024, 1, 1)


def _value(rng: random.Random, code: str) -> str:
    _, lo, hi, dec = TESTS[code]
    v = rng.uniform(lo, hi)
    return f"{v:.{dec}f}"


def _day(rng: random.Random) -> date:
    return Q1_START + timedelta(days=rng.randrange(91))


def build():
    rng = random.Random(SEED)

    # ---- crosswalk -------------------------------------------------------
    site_a_ids = [f"A{1001 + i}" for i in range(12)]
    site_b_ids = [f"B-{201 + i:04d}" for i in range(10)]
    site_c_ids = [4410 + 7 * i for i in range(8)]
    xwalk = []
    for i, lid in enumerate(site_a_ids):
        xwalk.append(("site_a", lid, f"P{1 + i:04d}"))
    for i, lid in enumerate(site_b_ids):
        # site_b patients 0..2 are the same people as site_a patients 4..6
        gid = f"P{5 + i:04d}" if i < 3 else f"P{20 + i:04d}"
        xwalk.append(("site_b", lid, gid))
    for i, lid in enumerate(site_c_ids):
        xwalk.append(("site_c", str(lid), f"P{40 + i:04d}"))
    # fanout traps: A1003 appears three times (exact dup + messy-but-same key)
    xwalk.insert(9, ("site_a", "A1003", "P0003"))
    xwalk.append(("site_a", " a1003 ", "P0003"))

    # ---- site A: CSV, ISO dates -----------------------------------------
    names_a = SITE_TEST_NAMES["site_a"]
    rows_a = []
    for _ in range(30):
        code = rng.choice(list(TESTS))
        rows_a.append([rng.choice(site_a_ids), names_a[code], _value(rng, code),
                       TESTS[code][0], _day(rng).isoformat(),
                       rng.choice(["", "", "", "fasting", "AM draw"])])
    planted_a = [
        ["A1001", "  glucose, fasting ", "101", "mg/dL", "2024-01-15", ""],        # ok
        ["A1002", "Vitamin D", "31.2", "ng/mL", "2024-01-20", ""],                  # unmapped_test
        ["A9999", "Potassium", "4.1", "mmol/L", "2024-02-02", ""],                  # unknown_patient
        ["A1004", "Creatinine", "0.91", "mg/dL", "2024-13-01", ""],                 # bad_date
        ["A1005", "Hemoglobin", "pending", "g/dL", "2024-02-11", ""],              # non_numeric
        ["A1006", "HEMOGLOBIN A1C", "6.4", "%", "2024-03-03",
         'hemolyzed, "redraw" requested'],                                         # ok, quoted
        [" a1003", "Potassium", "4.4", "mmol/L", "2024-03-09", ""],                 # ok, messy id
        ["A1007", "Glucose, Fasting", "NaN", "mg/dL", "2024-03-12", ""],            # non_numeric
        ["A9998", "Vitamin D", "28.0", "ng/mL", "2024-03-14", ""],                  # unmapped (1st rule)
        ["A1003", "Hemoglobin", "13.9", "g/dL", "2024-03-20", "AM draw, fasting"],  # ok, fanout probe
    ]
    for k, row in enumerate(planted_a):
        rows_a.insert(3 + 3 * k, row)

    # ---- site B: TSV, US dates, extra column ----------------------------
    names_b = SITE_TEST_NAMES["site_b"]
    rows_b = []
    for _ in range(25):
        code = rng.choice(list(TESTS))
        rows_b.append([rng.choice(site_b_ids), names_b[code], _value(rng, code),
                       TESTS[code][0], _day(rng).strftime("%m/%d/%Y"),
                       rng.choice(["", "", "see chart, repeat"]),
                       rng.choice(["ED", "IM", "FM"])])
    planted_b = [
        ["B-0202", "a1c", "7.1", "%", "01/09/2024", "", "IM"],           # ok, case
        ["B-0203", "TSH", "2.2", "mIU/L", "01/18/2024", "", "FM"],       # unmapped_test
        ["B-0204", "GLUC", "88", "mg/dL", "02/30/2024", "", "ED"],       # bad_date (no Feb 30)
        ["B-0205", "K+", "4.0", "mmol/L", "2024-02-10", "", "ED"],       # bad_date (ISO at US site)
        ["b-0203", "HGB", "12.8", "g/dL", "02/21/2024", "", "IM"],       # ok, lowercase id
        ["B-0206", "CREA", "", "mg/dL", "03/01/2024", "", "IM"],         # non_numeric (empty)
        ["B-0207", "GLUC", " 5.1 ", "mmol/L", "03/05/2024", "", "FM"],   # ok, padded value
        ["B-0201", " k+ ", "3.9", "mmol/L", "03/28/2024", "repeat, hemolyzed", "ED"],  # ok
    ]
    for k, row in enumerate(planted_b):
        rows_b.insert(2 + 3 * k, row)

    # ---- site C: Parquet, int ids, float results, timestamp strings -----
    names_c = SITE_TEST_NAMES["site_c"]
    pid, lab, res, unit, ts = [], [], [], [], []

    def add_c(p, l, r, u, t):
        pid.append(p); lab.append(l); res.append(r); unit.append(u); ts.append(t)

    for _ in range(20):
        code = rng.choice(list(TESTS))
        d = _day(rng)
        add_c(rng.choice(site_c_ids), names_c[code], float(_value(rng, code)), TESTS[code][0],
              f"{d.isoformat()} {rng.randrange(6, 18):02d}:{rng.choice([0, 15, 30, 45]):02d}:00")
    planted_c = [
        (4410, "glucose_serum", None, "mg/dL", "2024-01-05 08:00:00"),       # non_numeric (null)
        (4417, "potassium_serum", 4.2, "mmol/L", "2024-02-30 09:00:00"),    # bad_date
        (9999, "hemoglobin_bld", 14.1, "g/dL", "2024-02-14 10:30:00"),      # unknown_patient
        (4424, "HbA1c_Pct", 5.9, "%", "2024-03-18 07:45:00"),               # ok, case
    ]
    for k, (p, l, r, u, t) in enumerate(planted_c):
        at = 1 + 4 * k
        pid.insert(at, p); lab.insert(at, l); res.insert(at, r); unit.insert(at, u); ts.insert(at, t)

    table = pa.table({
        "pid": pa.array(pid, type=pa.int64()),
        "lab_name": pa.array(lab, type=pa.string()),
        "result": pa.array(res, type=pa.float64()),
        "result_unit": pa.array(unit, type=pa.string()),
        "collection_ts": pa.array(ts, type=pa.string()),
    })
    return xwalk, rows_a, rows_b, table


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    xwalk, rows_a, rows_b, table_c = build()

    mappings = {}
    for site, m in MAPPINGS.items():
        m = dict(m)
        m["test_map"] = {name: code for code, name in SITE_TEST_NAMES[site].items()}
        mappings[site] = m
    (DATA / "mappings.json").write_text(json.dumps(mappings, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")

    with open(DATA / "patient_crosswalk.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site_id", "local_patient_id", "patient_id"])
        w.writerows(xwalk)

    with open(DATA / "site_a_labs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["MRN", "TestName", "ResultValue", "Units", "CollectedDate", "Comment"])
        w.writerows(rows_a)

    with open(DATA / "site_b_labs.tsv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["patient_ref", "test", "value", "unit", "date_collected", "notes",
                    "ordering_dept"])
        w.writerows(rows_b)

    pq.write_table(table_c, DATA / "site_c_labs.parquet", compression="snappy")
    print(f"wrote {len(rows_a)} site_a rows, {len(rows_b)} site_b rows, "
          f"{table_c.num_rows} site_c rows, {len(xwalk)} crosswalk rows to {DATA}")


if __name__ == "__main__":
    main()
