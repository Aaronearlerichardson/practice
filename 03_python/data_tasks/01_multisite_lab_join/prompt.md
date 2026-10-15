# 01. Three sites, one lab table

**Timebox: 35 min** | Write: `03_python/data_tasks/01_multisite_lab_join/solution.py`

## Input

Files in `data/`. `run(data_dir, out_dir)` gets this folder as `data_dir`.
`python gen_data.py` regenerates `data/` byte-identically.

File: `site_a_labs.csv` (comma-separated, header row, 40 data rows)

```text
+---------------+------+------------------------------------------+
| Column Name   | Type | Notes                                    |
+---------------+------+------------------------------------------+
| MRN           | text | maps to local_patient_id                 |
| TestName      | text | maps to local_test_name                  |
| ResultValue   | text | maps to value                            |
| Units         | text | maps to unit                             |
| CollectedDate | text | maps to collected_date; YYYY-MM-DD       |
| Comment       | text | maps to comment; free text, can be blank |
+---------------+------+------------------------------------------+
```

File: `site_b_labs.tsv` (tab-separated, header row, 33 data rows)

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

File: `site_c_labs.parquet` (24 rows)

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

site_c has no comment column.

File: `mappings.json`, one object per `site_id` (`site_a`, `site_b`, `site_c`)

```text
+-------------+----------------+------------------------------------------+
| Key         | Type           | Notes                                    |
+-------------+----------------+------------------------------------------+
| file        | str            | the site's file name in data/            |
| format      | str            | 'csv', 'tsv' or 'parquet'                |
| date_format | str            | strptime format for collected_date       |
| columns     | dict[str, str] | site column -> standard field (above)    |
| test_map    | dict[str, str] | site test name -> test_code (below)      |
+-------------+----------------+------------------------------------------+
```

What the file holds:

```text
+---------+---------------------+---------+-------------------+
| site_id | file                | format  | date_format       |
+---------+---------------------+---------+-------------------+
| site_a  | site_a_labs.csv     | csv     | %Y-%m-%d          |
| site_b  | site_b_labs.tsv     | tsv     | %m/%d/%Y          |
| site_c  | site_c_labs.parquet | parquet | %Y-%m-%d %H:%M:%S |
+---------+---------------------+---------+-------------------+

test_map keys (site test names), by the test_code they map to:
+-----------+------------------+--------+------------------+
| test_code | site_a           | site_b | site_c           |
+-----------+------------------+--------+------------------+
| GLU       | Glucose, Fasting | GLUC   | glucose_serum    |
| HBA1C     | Hemoglobin A1c   | A1C    | hba1c_pct        |
| K         | Potassium        | K+     | potassium_serum  |
| CREAT     | Creatinine       | CREA   | creatinine_serum |
| HGB       | Hemoglobin       | HGB    | hemoglobin_bld   |
+-----------+------------------+--------+------------------+
```

File: `patient_crosswalk.csv` (comma-separated, header row, 32 data rows)

```text
+------------------+------+-----------------------------------+
| Column Name      | Type | Notes                             |
+------------------+------+-----------------------------------+
| site_id          | text | 'site_a', 'site_b' or 'site_c'    |
| local_patient_id | text | the site's own patient id         |
| patient_id       | text | global id, e.g. 'P0001'           |
+------------------+------+-----------------------------------+
```

Maps each site's local patient id to the global `patient_id`. Look at it
before you write the join: some keys repeat.

Three sites each deliver Q1 2024 lab results in their own shape. Your job is
the step a Glue job does before data lands in bronze: map every site onto one
schema and one patient identity, and send anything you can't map to a rejects
file with a reason.

## Task

**Goal:** every data row of the three site files lands in exactly one of two
CSV files. A row that passes all four rules becomes one row of
`labs_standardized.csv`, with the global `patient_id`, a `test_code`, an ISO
date and a number. A row that fails a rule becomes one row of
`labs_rejects.csv`, with the first rule it fails as `reject_reason`.

Step 1 is `load_mappings`, step 2 is `load_crosswalk`, step 3 is `read_site`,
steps 4-6 are `standardize_rows`, and steps 7-8 are `run`.

1. **Load the mappings.** `load_mappings(path)` reads `mappings.json` and
   returns it as a dict: `site_id` -> that site's object (`file`, `format`,
   `date_format`, `columns`, `test_map`).
2. **Load the crosswalk.** `load_crosswalk(path)` reads
   `patient_crosswalk.csv`. For each row, the key is
   (`site_id.strip()`, `local_patient_id.strip().upper()`) and the value is
   `patient_id`. Rows with the same key and the same `patient_id` give one
   entry. If one key appears with two different `patient_id` values, raise
   `ValueError`: don't guess an identity. Return the dict.
3. **Read one site's file.** `read_site(data_dir, site_id, mapping)` reads
   `data_dir / mapping["file"]`. Format `csv` is comma-separated and `tsv` is
   tab-separated, both UTF-8 with a header row; `parquet` is a Parquet file.
   Rename each column with `mapping["columns"]` (site column -> standard
   field), and drop any column it doesn't list (site_b's `ordering_dept`).
   Return one dict per data row, in file order, with exactly the keys
   `local_patient_id`, `local_test_name`, `value`, `unit`, `collected_date`,
   `comment` and `source_row`. Every value is a `str`:
   - CSV and TSV text stays exactly as in the file: not trimmed, not checked.
   - A Parquet value is converted with `str()` (`4410` -> `'4410'`, `4.2` ->
     `'4.2'`). A null becomes `''`.
   - A field the site doesn't send (site_c's `comment`) is `''`.
   - `source_row` is the 1-based data row number, header excluded (`'1'` for
     the first data row).
4. **Check the four rules, in order.**
   `standardize_rows(site_id, rows, mapping, crosswalk)` checks each step 3
   row against these rules, in this order. The first rule the row fails is
   its `reject_reason`, and the later rules are not checked.
   1. `unmapped_test`: `local_test_name.strip().casefold()` equals no key of
      `mapping["test_map"]` after `.casefold()`. (`'  glucose, fasting '`
      matches the key `'Glucose, Fasting'`.)
   2. `unknown_patient`: (`site_id`, `local_patient_id.strip().upper()`) is
      not a key of the step 2 crosswalk.
   3. `bad_date`:
      `datetime.strptime(collected_date.strip(), mapping["date_format"])`
      raises. A real date in the wrong format fails too: `'2024-02-10'` at
      site_b (`%m/%d/%Y`) is `bad_date`.
   4. `non_numeric_value`: `float(value.strip())` raises, or its result is
      not finite. So `''`, `'pending'`, `'NaN'` and `'inf'` all fail.
5. **Build the reject rows.** For each row that failed: `site_id` (the
   argument), then `source_row`, `local_patient_id`, `local_test_name`,
   `value` and `collected_date` exactly as step 3 returned them (raw, not
   trimmed), then `reject_reason` from step 4.
6. **Build the standardized rows.** For each row that passed all four rules:
   - `patient_id`: the crosswalk value for the rule 2 key.
   - `collected_date`: the date parsed in rule 3, as `YYYY-MM-DD` (site_c's
     time of day is dropped).
   - `test_code`: the `test_map` value of the key that matched in rule 1.
   - `value`: the float from rule 4.
   - `unit`: `unit.strip()`.
   - `site_id`: the argument.
   - `source_row`: from step 3.
   - `comment`: from step 3, unchanged (not trimmed).

   Return (standardized rows, reject rows).
7. **Run every site and sort.** `run(data_dir, out_dir)` loads
   `data_dir/mappings.json` (step 1) and `data_dir/patient_crosswalk.csv`
   (step 2), then runs steps 3-6 for each `site_id` in `mappings.json`. Sort
   all standardized rows by (`patient_id`, `collected_date`, `test_code`,
   `site_id`, `source_row`), and all reject rows by (`site_id`,
   `source_row`). Compare `source_row` as a number (`2` before `10`).
8. **Write the files and count.** Create `out_dir` if it doesn't exist. Write
   `labs_standardized.csv` and `labs_rejects.csv`: UTF-8, comma-separated, a
   header row, then the rows in step 7 order. Quote fields the way
   `csv.writer` does, so a comment holding commas or quotes reads back
   unchanged. Return `{"written": n, "rejected": n}`: the row counts of the
   two files.

## Output

| function | returns |
|---|---|
| `load_mappings(path)` | `dict[str, dict]`: `site_id` -> its `mappings.json` object |
| `load_crosswalk(path)` | `dict[tuple[str, str], str]`: (`site_id`, `LOCAL_ID`) -> `patient_id` (step 2) |
| `read_site(data_dir, site_id, mapping)` | `list[dict[str, str]]`: one dict per data row (step 3) |
| `standardize_rows(site_id, rows, mapping, crosswalk)` | (standardized rows, reject rows): two lists of dicts, keyed by the file columns below |
| `run(data_dir, out_dir)` | `{"written": n, "rejected": n}`: row counts of the two files |

File `out_dir/labs_standardized.csv`, columns in this order. Rows sorted by
(`patient_id`, `collected_date`, `test_code`, `site_id`, `source_row` as a
number).

| # | column | notes |
|---|---|---|
| 1 | patient_id | crosswalk value for (`site_id`, `local_patient_id.strip().upper()`) |
| 2 | collected_date | `collected_date.strip()` parsed with the site's `date_format`, written `YYYY-MM-DD` |
| 3 | test_code | `test_map` value of the key that matches `local_test_name.strip()`, ignoring case |
| 4 | value | `float(value.strip())`, written with `str()` (`101` -> `101.0`). The tests read it back with `float()`, so any text for the same float passes |
| 5 | unit | `unit.strip()` |
| 6 | site_id | the `mappings.json` key: `site_a`, `site_b` or `site_c` |
| 7 | source_row | 1-based data row number in the site's file, header excluded |
| 8 | comment | `comment` from step 3, unchanged; `''` for site_c |

File `out_dir/labs_rejects.csv`, columns in this order. Rows sorted by
(`site_id`, `source_row` as a number).

| # | column | notes |
|---|---|---|
| 1 | site_id | the `mappings.json` key |
| 2 | source_row | 1-based data row number in the site's file |
| 3 | local_patient_id | raw, from step 3 |
| 4 | local_test_name | raw, from step 3 |
| 5 | value | raw, from step 3 (`''` for a Parquet null) |
| 6 | collected_date | raw, from step 3 |
| 7 | reject_reason | the first rule failed in step 4: `unmapped_test`, `unknown_patient`, `bad_date` or `non_numeric_value` |

## Example

Try it on your code (inputs editable): `python tasks.py try data 01`.

`mappings.json` is the real file (tables in Input). The other four files:

`patient_crosswalk.csv`:

```text
site_id,local_patient_id,patient_id
site_a,A1001,P0001
site_a,A1003,P0003
site_a, a1003 ,P0003
site_b,B-0201,P0005
site_c,4410,P0040
```

`site_a_labs.csv` (row 1 starts with a space):

```text
MRN,TestName,ResultValue,Units,CollectedDate,Comment
 a1003,Hemoglobin,13.9, g/dL ,2024-03-20,"hemolyzed, ""redraw"" requested"
A1001,"  glucose, fasting ",101,mg/dL,2024-01-15,
A9998,Vitamin D,28.0,ng/mL,2024-03-14,
A1001,Creatinine,0.91,mg/dL,2024-13-01,
A1003,"Glucose, Fasting",NaN,mg/dL,2024-03-12,
```

`site_b_labs.tsv` (values shown in quotes to make the spaces visible; the
file has tabs and no quotes):

```text
+-------------+--------+---------+----------+----------------+---------------------+---------------+
| patient_ref | test   | value   | unit     | date_collected | notes               | ordering_dept |
+-------------+--------+---------+----------+----------------+---------------------+---------------+
| 'b-0201'    | ' k+ ' | ' 5.1 ' | 'mmol/L' | '03/28/2024'   | 'repeat, hemolyzed' | 'ED'          |
| 'B-0201'    | 'A1C'  | '7.1'   | '%'      | '2024-02-10'   | ''                  | 'IM'          |
| 'b-0299'    | 'GLUC' | '88'    | 'mg/dL'  | '01/09/2024'   | ''                  | 'FM'          |
+-------------+--------+---------+----------+----------------+---------------------+---------------+
```

`site_c_labs.parquet`:

```text
+------+---------------+--------+-------------+---------------------+
| pid  | lab_name      | result | result_unit | collection_ts       |
+------+---------------+--------+-------------+---------------------+
| 4410 | HbA1c_Pct     | 5.9    | %           | 2024-03-18 07:45:00 |
| 4410 | glucose_serum | null   | mg/dL       | 2024-01-05 08:00:00 |
+------+---------------+--------+-------------+---------------------+
```

Output: `run(data_dir, out_dir)` returns `{'written': 4, 'rejected': 6}` and
writes these two files.

`labs_standardized.csv`:

```text
patient_id,collected_date,test_code,value,unit,site_id,source_row,comment
P0001,2024-01-15,GLU,101.0,mg/dL,site_a,2,
P0003,2024-03-20,HGB,13.9,g/dL,site_a,1,"hemolyzed, ""redraw"" requested"
P0005,2024-03-28,K,5.1,mmol/L,site_b,1,"repeat, hemolyzed"
P0040,2024-03-18,HBA1C,5.9,%,site_c,1,
```

`labs_rejects.csv`:

```text
site_id,source_row,local_patient_id,local_test_name,value,collected_date,reject_reason
site_a,3,A9998,Vitamin D,28.0,2024-03-14,unmapped_test
site_a,4,A1001,Creatinine,0.91,2024-13-01,bad_date
site_a,5,A1003,"Glucose, Fasting",NaN,2024-03-12,non_numeric_value
site_b,2,B-0201,A1C,7.1,2024-02-10,bad_date
site_b,3,b-0299,GLUC,88,01/09/2024,unknown_patient
site_c,2,4410,glucose_serum,,2024-01-05 08:00:00,non_numeric_value
```

Explanation:

- **Step 1.** The mappings are the real ones: site_b dates are `%m/%d/%Y`,
  site_c dates carry a time, and each site has its own test names.
- **Step 2.** The 5 crosswalk rows give 4 keys. `A1003` and ` a1003 ` both
  become (`site_a`, `A1003`) -> `P0003`, so they collapse to one entry. If the
  file also had the row `site_a, a1001,P0002`, the key (`site_a`, `A1001`)
  would map to both `P0001` and `P0002`, and `load_crosswalk` would raise
  `ValueError`.
- **Step 3.** site_a row 1 comes back as `' a1003'`, space included. site_b
  loses `ordering_dept`. site_c row 1 comes back as `'4410'` and `'5.9'`, and
  row 2's null `result` as `''`. Every site_c `comment` is `''`.
- **Step 4.** site_a row 3 fails rule 1 (`Vitamin D` is not a site_a test
  name), so it is `unmapped_test`, even though `A9998` would fail rule 2 too.
  site_b row 3: `B-0299` is not in the crosswalk: `unknown_patient`. site_a
  row 4 has month 13 and site_b row 2 is `YYYY-MM-DD` at a `%m/%d/%Y` site:
  both `bad_date`. site_a row 5: `float('NaN')` works, but NaN is not finite:
  `non_numeric_value`. site_c row 2's `''` is `non_numeric_value` too. The
  messy names pass rule 1: `'  glucose, fasting '`, `' k+ '` and `HbA1c_Pct`.
- **Step 5.** Reject rows keep the raw text: `b-0299` stays lowercase, `NaN`
  stays `NaN`, and site_c row 2's `value` is empty.
- **Step 6.** site_a row 1: `' a1003'` -> `A1003` -> `P0003`, written once
  (the repeated crosswalk rows don't make extra copies). Its unit `' g/dL '`
  becomes `g/dL`. site_a row 2: `101` -> `101.0`. site_b row 1: `' 5.1 '` ->
  `5.1` and `03/28/2024` -> `2024-03-28`. site_c row 1:
  `2024-03-18 07:45:00` -> `2024-03-18`.
- **Step 7.** site_a row 2 (`P0001`) comes before site_a row 1 (`P0003`):
  rows sort by `patient_id` first, not by file order.
- **Step 8.** The two comments that hold commas are quoted, and the `"`
  inside the site_a comment is doubled, so it reads back as
  `hemolyzed, "redraw" requested`. 4 written + 6 rejected = 10 input rows.

## Implement (in `solution.py`)

```python
def load_mappings(path) -> dict[str, dict]
def load_crosswalk(path) -> dict[tuple[str, str], str]           # (site_id, LOCAL_ID) -> patient_id
def read_site(data_dir, site_id, mapping) -> list[dict[str, str]]  # LOCAL_FIELDS + source_row, all str
def standardize_rows(site_id, rows, mapping, crosswalk) -> tuple[list[dict], list[dict]]
def run(data_dir, out_dir) -> dict[str, int]                     # {"written": n, "rejected": n}
```

Keep the names and signatures: the tests import them. The docstrings in
`solution.py` are part of the spec. Standard library, pandas, or pyarrow: your
call.

## Run the tests (PowerShell, from the repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest 03_python\data_tasks\01_multisite_lab_join -q -p no:cacheprovider
```

<details><summary>Hints</summary>

- `pd.read_csv` turns `"NaN"` and `""` into float NaN and may turn ids into ints. If you use pandas, pass `dtype=str, keep_default_na=False`. The `csv` module never guesses.
- Parquet keeps its types: `pid` comes back as an int and `result` as a float. A null `result` is `None` from pyarrow's `to_pylist()` but NaN from pandas. Convert to str deliberately, with null becoming `""`.
- `float("NaN")` succeeds. That's why rule 4 says *finite*.
- Normalize keys in one place (a `norm_id` helper) and use it on both sides of every lookup.
- A dict keyed by the normalized crosswalk key can't fan out. A `merge` against a crosswalk with duplicate keys can.

</details>

<details><summary>Check yourself</summary>

- Written **84** (site_a 34, site_b 29, site_c 21). Rejected **13**: `unmapped_test` 3, `unknown_patient` 2, `bad_date` 4, `non_numeric_value` 4. Every one of the 97 input rows (40 + 33 + 24) is in exactly one output.
- `load_crosswalk` returns **30** keys from the 32 crosswalk rows.
- Patient `P0003` has **4** rows. If you see more (12 is the classic), your join fanned out on the duplicate crosswalk key. If you see 3, you did not normalize ids.
- site_a row 28 has both an unmapped test and an unknown patient: it's `unmapped_test`.
- site_b row 12 is an ISO date at a US-format site: `bad_date`, not a silent reinterpretation.
- The site_a comment `hemolyzed, "redraw" requested` survives byte-for-byte.

</details>

## Say it out loud

- **Restate:** three shapes in, one schema out, identity resolved through a crosswalk, nothing silently dropped (written + rejected = read).
- **Edge cases:** whitespace and case in codes and ids, duplicate crosswalk keys (agreeing vs conflicting), NaN parsing as a float, a valid-looking date in the wrong format, nulls from a typed format, quoted commas.
- **Plan:** read each site into the same local shape, normalize keys once, build the crosswalk as a dict, apply rules in order, sort, write two files.
- **Complexity:** O(n) to read and check, O(n log n) to sort. Memory is O(n) for the rows you hold to sort, plus O(crosswalk) for the dict.
- **At 100x:** stream each file instead of loading it, and keep the crosswalk in memory (it's small) or broadcast-join it in Spark. Fail the load if the reject rate jumps instead of quietly writing fewer rows.
- **Pedestal mapping:** `mappings.json` is the per-site config a Glue job reads, and rejects are a quarantine table. The crosswalk is a dbt `ref`. Its uniqueness is a dbt `unique` test on `(site_id, local_patient_id)` that should fail the build, not get deduped downstream. The fill rate and plausibility of `value` belong in silver quality checks.
