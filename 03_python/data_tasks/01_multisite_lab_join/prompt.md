# 01. Three sites, one lab table

**Timebox: 35 min**

## Input

Files in `data/`. `run(data_dir, out_dir)` gets this folder as `data_dir`, and `read_site(data_dir, site_id, mapping)` reads one site's file. `python gen_data.py` regenerates `data/` byte-identically.

File: `site_a_labs.csv` (comma-separated, header row)

```text
+---------------+------+------------------------------------------+
| Column Name   | Type | Notes                                    |
+---------------+------+------------------------------------------+
| MRN           | text | maps to local_patient_id                 |
| TestName      | text | maps to local_test_name                  |
| ResultValue   | text | maps to value                            |
| Units         | text | maps to unit                             |
| CollectedDate | text | maps to collected_date; ISO YYYY-MM-DD   |
| Comment       | text | maps to comment; free text, can be blank |
+---------------+------+------------------------------------------+
```

File: `site_b_labs.tsv` (tab-separated, header row)

```text
+----------------+------+--------------------------------------------+
| Column Name    | Type | Notes                                      |
+----------------+------+--------------------------------------------+
| patient_ref    | text | maps to local_patient_id                   |
| test           | text | maps to local_test_name                    |
| value          | text | maps to value                              |
| unit           | text | maps to unit                               |
| date_collected | text | maps to collected_date; US date MM/DD/YYYY |
| notes          | text | maps to comment; free text, can be blank   |
| ordering_dept  | text | not mapped; you don't need it              |
+----------------+------+--------------------------------------------+
```

File: `site_c_labs.parquet`

```text
+---------------+---------+-----------------------------------------------+
| Column Name   | Type    | Notes                                         |
+---------------+---------+-----------------------------------------------+
| pid           | int64   | maps to local_patient_id                      |
| lab_name      | string  | maps to local_test_name                       |
| result        | float64 | maps to value; can be null                    |
| result_unit   | string  | maps to unit                                  |
| collection_ts | string  | maps to collected_date; 'YYYY-MM-DD HH:MM:SS' |
+---------------+---------+-----------------------------------------------+
```

File: `mappings.json`, one object per site_id (`site_a`, `site_b`, `site_c`)

```text
+-------------+----------------+---------------------------------------------------------+
| Key         | Type           | Notes                                                   |
+-------------+----------------+---------------------------------------------------------+
| file        | str            | the site's file name in data/                           |
| format      | str            | csv, tsv or parquet                                     |
| date_format | str            | strptime format for collected_date                      |
| columns     | dict[str, str] | site column -> standard field                           |
| test_map    | dict[str, str] | site test name -> test code (GLU, HBA1C, K, CREAT, HGB) |
+-------------+----------------+---------------------------------------------------------+
```

File: `patient_crosswalk.csv` (comma-separated, header row)

```text
+------------------+------+---------------------------+
| Column Name      | Type | Notes                     |
+------------------+------+---------------------------+
| site_id          | text | site_a, site_b or site_c  |
| local_patient_id | text | the site's own patient id |
| patient_id       | text | global id, e.g. 'P0001'   |
+------------------+------+---------------------------+
```

Maps each site's local id to the global `patient_id`.

The standard local fields are `local_patient_id, local_test_name, value, unit, collected_date, comment`. A site that doesn't send one of them (site_c has no comment) gets `""`.

Same shape as the screen (read a file, look up a key in a reference table, write a standardized CSV), but now three sites each deliver Q1 2024 lab results in their own shape. Your job is the step a Glue job does before data lands in bronze: map every site onto one schema and one patient identity, and send anything you can't map to rejects with a reason.

## Outputs (`out_dir/`)

**`labs_standardized.csv`**, columns in this order:

`patient_id, collected_date, test_code, value, unit, site_id, source_row, comment`

- `collected_date` is ISO `YYYY-MM-DD` (drop any time part).
- `value` is the parsed number (any text that parses back to the same float is fine, e.g. `101.0`).
- `unit` is trimmed. `comment` is passed through unchanged.
- `source_row` is the 1-based data row number in the site's file (header excluded).
- Sort by `patient_id, collected_date, test_code, site_id, source_row` (source_row numerically).

**`labs_rejects.csv`**, columns in this order:

`site_id, source_row, local_patient_id, local_test_name, value, collected_date, reject_reason`

- Raw values as read from the file (untrimmed; nulls become `""`). Sort by `site_id, source_row`.

## Rules (apply in order; the first rule that fails is the reason)

| # | Rule | Reject reason |
|---|---|---|
| 1 | Test name, after trimming and case-folding, must match a `test_map` key (also case-folded) for that site | `unmapped_test` |
| 2 | `(site_id, local_patient_id)` must be in the crosswalk. Local ids are matched after trimming and uppercasing, on both sides | `unknown_patient` |
| 3 | `collected_date`, trimmed, must parse with the site's `date_format` | `bad_date` |
| 4 | `value`, trimmed, must parse as a finite float (empty, null, `NaN`, `inf` all fail) | `non_numeric_value` |

Crosswalk rules: duplicate rows that agree (after normalization) collapse to one. If the same normalized key maps to two different `patient_id`s, `load_crosswalk` raises `ValueError`: don't guess an identity.

Look at the crosswalk before you write the join.

## Implement (in `solution.py`)

```python
def load_mappings(path) -> dict[str, dict]
def load_crosswalk(path) -> dict[tuple[str, str], str]           # (site_id, LOCAL_ID) -> patient_id
def read_site(data_dir, site_id, mapping) -> list[dict[str, str]]  # LOCAL_FIELDS + source_row, all str
def standardize_rows(site_id, rows, mapping, crosswalk) -> tuple[list[dict], list[dict]]
def run(data_dir, out_dir) -> dict[str, int]                     # {"written": n, "rejected": n}
```

The docstrings in `solution.py` are part of the spec. Standard library, pandas, or pyarrow: your call.

## Run the tests (PowerShell, from the repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest 03_python\data_tasks\01_multisite_lab_join -q -p no:cacheprovider
```

<details><summary>Hints</summary>

- `pd.read_csv` turns `"NaN"` and `""` into float NaN and may turn ids into ints. If you use pandas, pass `dtype=str, keep_default_na=False`. The `csv` module never guesses.
- Parquet keeps its types: `pid` comes back as an int and `result` as a float or None. Convert to str deliberately, with null becoming `""`.
- `float("NaN")` succeeds. That's why rule 4 says *finite*.
- Normalize keys in one place (a `norm_id` helper) and use it on both sides of every lookup.
- A dict keyed by the normalized crosswalk key can't fan out. A `merge` against a crosswalk with duplicate keys can.

</details>

<details><summary>Check yourself</summary>

- Written **84** (site_a 34, site_b 29, site_c 21). Rejected **13**: `unmapped_test` 3, `unknown_patient` 2, `bad_date` 4, `non_numeric_value` 4. Every one of the 97 input rows is in exactly one output.
- Patient `P0003` has **4** rows. If you see more (12 is the classic), your join fanned out on the duplicate crosswalk key. If you see 3, you did not normalize ids.
- site_a row 28 has both an unmapped test and an unknown patient: it's `unmapped_test`.
- site_b row 12 is an ISO date at a US-format site: `bad_date`, not a silent reinterpretation.
- The site_a comment `hemolyzed, "redraw" requested` survives byte-for-byte.

</details>

## Say it out loud

- **Restate:** three shapes in, one schema out, identity resolved through a crosswalk, nothing silently dropped (written + rejected = read).
- **Edge cases:** whitespace and case in codes and ids, duplicate crosswalk keys (agreeing vs conflicting), NaN parsing as a float, a valid-looking date in the wrong format, nulls from a typed format, quoted commas.
- **Plan:** read each site into the same local shape, normalize keys once, build the crosswalk as a dict, apply rules in order, sort, write two files.
- **Complexity:** O(n) to read and check, O(n log n) to sort, O(crosswalk) memory.
- **At 100x:** stream each file instead of loading it, and keep the crosswalk in memory (it's small) or broadcast-join it in Spark. Fail the load if the reject rate jumps instead of quietly writing fewer rows.
- **Pedestal mapping:** `mappings.json` is the per-site config a Glue job reads, and rejects are a quarantine table. The crosswalk is a dbt `ref`. Its uniqueness is a dbt `unique` test on `(site_id, local_patient_id)` that should fail the build, not get deduped downstream. The fill rate and plausibility of `value` belong in silver quality checks.
