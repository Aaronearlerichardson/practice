# 04. What changed since last quarter?

**Timebox: 40 min**

Site X sends a lab extract every quarter, and the "same" file never stays the same. Before a Glue job casts these columns into an Iceberg table, you want a report that says exactly what drifted, so a silent rename doesn't become a column of nulls in silver. Build the schema profiler and the diff.

## Inputs (`data/`)

`site_x_2024Q1.csv` through `site_x_2024Q4.csv`: about 100 rows each. `python gen_data.py` regenerates them byte-identically. Several kinds of drift are planted, and so is one change that is **not** drift.

## Step 1: profile a file, `infer_schema(path) -> dict[str, ColumnInfo]`

One `ColumnInfo(name, type, fmt, fill_rate, categories)` per column, keyed by name in file order. Values are **stripped** first, and an empty value is `""` after stripping.

| Field | Definition |
|---|---|
| `type` | The **narrowest** type that fits **every non-empty value**, checked in this order: `int` (regex `[+-]?\d+`), `float` (regex `[+-]?(\d+\.?\d*\|\.\d+)([eE][+-]?\d+)?`), `date` (one format from `DATE_FORMATS` parses all values), `datetime` (one format from `DATETIME_FORMATS` parses all values), else `string`. A column with no non-empty values is `string`. `nan`/`inf` are strings. |
| `fmt` | For `date`/`datetime`: the **first** format in the list that parses every non-empty value. Otherwise `None`. |
| `fill_rate` | non-empty count / row count, rounded to 4 decimals |
| `categories` | `frozenset` of distinct non-empty values if there are at most `MAX_CATEGORIES` (20), else `None` |

`DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y"]`
`DATETIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M"]`

## Step 2: diff two profiles, `compare(prev, curr) -> list[Drift]`

**Match columns first:** (a) same exact name. (b) Among the leftovers, a prev column and a curr column whose `normalize_name` (lowercase, drop everything except `a-z0-9`) is equal are a **rename**, but only if exactly one leftover on each side has that normalized name. (c) Leftover prev columns are `removed`, leftover curr columns are `added`.

**Then, for each matched pair:**

| kind | when | `column` |
|---|---|---|
| `added` / `removed` | from matching | the curr name / the prev name |
| `renamed` | matched by normalized name | curr name (put the old name in `detail`) |
| `type_changed` | `prev.type != curr.type` | curr name |
| `date_format_changed` | same type, different `fmt` (never also reported with `type_changed`) | curr name |
| `fill_rate_drop` | `round(prev.fill_rate - curr.fill_rate, 4) > 0.20` (exactly 20 points is not a drop) | curr name |
| `new_values` | both sides have `categories`, and curr has values prev didn't (list them in `detail`) | curr name |

Column **order** is never drift. Return the list sorted by `(kind, column)`. `detail` is free text for humans.

## Step 3: report, `drift_report(paths) -> str`

Compare each consecutive pair (`paths[0]` to `paths[1]`, `paths[1]` to `paths[2]`, ...). Fewer than two paths raises `ValueError`. Format:

```markdown
# Schema drift report

## site_x_2024Q1.csv -> site_x_2024Q2.csv

| kind | column | detail |
|---|---|---|
| added | some_column | type string |

## a.csv -> b.csv

No drift.
```

Headings use file base names. Each drift is one row, `| {kind} | {column} | {detail} |`.

## Implement (in `solution.py`)

```python
def normalize_name(name: str) -> str
def infer_type(values: list[str]) -> tuple[str, str | None]
def infer_schema(path) -> dict[str, ColumnInfo]
def compare(prev, curr) -> list[Drift]
def drift_report(paths) -> str
```

## Run the tests (PowerShell, from the repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest 03_python\data_tasks\04_schema_drift -q -p no:cacheprovider
```

<details><summary>Hints</summary>

- Read with `csv.reader` and build one list of strings per column. Don't let pandas infer types for you: its rules aren't these rules, and `"nan"` becomes a float.
- `datetime.strptime("2024-01-02 08:00:00", "%Y-%m-%d")` raises (unconverted data remains), which is what keeps dates and datetimes apart.
- Do the rename matching on the leftovers only, after exact matches. A column that kept its name is never a rename.
- `0.9 - 0.7` is `0.20000000000000007` in floating point. That's why the rule rounds.
- Write `compare` against hand-built `ColumnInfo` dicts first. The tests do the same.

</details>

<details><summary>Check yourself</summary>

- Q1 -> Q2: **2** drifts (`added`, `fill_rate_drop`). One column also moved position: not drift.
- Q2 -> Q3: **3** drifts (`new_values`, `renamed`, `type_changed`).
- Q3 -> Q4: **2** drifts (`date_format_changed`, `removed`). One column's fill rate fell 15 points: not drift.
- A file compared with itself: `[]`.

</details>

## Say it out loud

- **Restate:** profile each file the same way, match columns (exact, then normalized), then diff the properties of each matched pair. The output is a contract check, not a data check.
- **Edge cases:** reorder only, an ambiguous rename, rename plus type change, date vs datetime, `nan` and `<0.5` in numeric columns, all-empty columns, float error at the threshold, high-cardinality columns (no category check).
- **Plan:** `infer_type` as a pure function over a list of strings, `infer_schema` = read + profile, `compare` = match + rules + sort, and the report is formatting only.
- **Complexity:** O(rows x cols) to profile, with date parsing the costly part. Cap the work by profiling a sample, or stop at the first value that fails each candidate type.
- **At 100x:** profile in one streaming pass with per-column running state (candidate types still alive, a non-empty count, a category set capped at 21). Profiles are tiny, so diffing them is free. Store each quarter's profile so you never re-read old files.
- **Pedestal mapping:** this is the gate in Step Functions before the Glue job writes. Glue crawlers and Iceberg schema evolution will happily *accept* an added column or a widened type, so silent acceptance is the risk. Renames are the dangerous one: Iceberg tracks columns by ID, but a site renaming a CSV header looks like drop + add, and silver gets nulls. The per-site column map from task 01 is where a confirmed rename gets fixed. Fill-rate and new-value checks become dbt tests (`not_null` with thresholds, `accepted_values`) in bronze/silver. A unit change like `%` to `mmol/mol` for HbA1c is a medical plausibility problem, not just a schema one: the values change by a factor of about 10.
