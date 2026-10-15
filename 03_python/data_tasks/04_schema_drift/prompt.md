# 04. What changed since last quarter?

**Timebox: 40 min** | Write: `03_python/data_tasks/04_schema_drift/solution.py`

## Input

Files in `data/`: `site_x_2024Q1.csv`, `site_x_2024Q2.csv`, `site_x_2024Q3.csv` and `site_x_2024Q4.csv`. One lab
extract per quarter from site X, 100 data rows each. `python gen_data.py` regenerates them byte-identically.

Each file is comma-separated with a header row and standard CSV quoting, and every value arrives as text. Every file
has at least one data row, and every row has as many fields as the header. The columns change from quarter to quarter
on purpose. Finding those changes is the task, so they aren't listed here. Several kinds of drift are planted, and so
is one change that is **not** drift.

Arguments:

- `values` (`list[str]`) for `infer_type(values)`: one column's values, as read.
- `path` for `infer_schema(path)`: one CSV path.
- `prev`, `curr` for `compare(prev, curr)`: two profiles, each a `dict[str, ColumnInfo]` keyed by column name, as
  `infer_schema` returns them. The tests also pass hand-built ones.
- `paths` for `drift_report(paths)`: a list of CSV paths, compared in list order.
- `name` (`str`) for `normalize_name(name)`: one column name.

Dataclass: `ColumnInfo` (in `solution.py`), one column's profile

```text
+------------+------------------------+-------------------------------------------------------+
| Field      | Type                   | Notes                                                 |
+------------+------------------------+-------------------------------------------------------+
| name       | str                    | column name, from the header row                      |
| type       | str                    | 'int', 'float', 'date', 'datetime' or 'string'        |
| fmt        | str or None            | strptime format for 'date'/'datetime', else None      |
| fill_rate  | float                  | non-empty values / data rows, rounded to 4 decimals   |
| categories | frozenset[str] or None | distinct non-empty values, or None when more than 20  |
+------------+------------------------+-------------------------------------------------------+
```

Step 2 defines each field exactly.

Constants (in `solution.py`):

- `DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y"]`
- `DATETIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M"]`
- `MAX_CATEGORIES = 20`
- `FILL_DROP_THRESHOLD = 0.20`

Site X sends a lab extract every quarter, and the "same" file never stays the same. Before a Glue job casts these
columns into an Iceberg table, you want a report that says exactly what drifted, so a silent rename doesn't become a
column of nulls in silver. Build the schema profiler and the diff.

## Task

**Goal:** profile every column of each file (`infer_schema`), list what changed between two profiles as `Drift`
objects (`compare`), and return one Markdown report with a section per consecutive pair of files (`drift_report`).

Step 1 is `infer_type(values)`. Step 2 is `infer_schema(path)`. Steps 3-6 are `compare(prev, curr)`, and step 3
is where `normalize_name(name)` is used. Step 7 is `drift_report(paths)`.

1. **Infer one column's type.** Strip every value. A value that is `""` after stripping is empty. Look only at the
   non-empty values. If there are none, return `('string', None)`. Otherwise return the first of these that fits
   every non-empty value:
   - `('int', None)`: every value fully matches the regex `[+-]?\d+`.
   - `('float', None)`: every value fully matches the regex `[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?`. Ints match it
     too, so a mix of `1` and `2.5` is float. `nan`, `inf` and `<0.5` don't match.
   - `('date', fmt)`: `fmt` is the first format in `DATE_FORMATS` for which `datetime.strptime(value, fmt)`
     succeeds on every value.
   - `('datetime', fmt)`: `fmt` is the first format in `DATETIME_FORMATS` for which `datetime.strptime(value, fmt)`
     succeeds on every value.
   - `('string', None)`: nothing above fits.

   All the values must fit one format: a mix of `2024-01-02` and `01/02/2024` is string, and so is a mix of
   `2024-01-02` and `2024-01-02 08:00:00`. `2024-02-30` is not a real date, so it is string too.
2. **Profile a file.** Read the CSV at `path`. For each column, in header order, build
   `ColumnInfo(name, type, fmt, fill_rate, categories)` from the column's values, each stripped:
   - `name`: the column's header text.
   - `type`, `fmt`: `infer_type` of the column's values (step 1).
   - `fill_rate`: `round(number of non-empty values / number of data rows, 4)`.
   - `categories`: `frozenset` of the distinct non-empty values when there are at most `MAX_CATEGORIES` (20) of
     them, else `None`. This applies to every type, so a small file keeps `categories` for every column.

   Return a `dict` of `name -> ColumnInfo`, with keys in header order.
3. **Match columns.** (a) A name that is a key of both `prev` and `curr` is a matched pair. (b) Among the names
   left over after (a), compare `normalize_name(name)`: the name lowercased, with every character that is not `a`-`z`
   or `0`-`9` dropped (`'Collected At (UTC)'` -> `'collectedatutc'`). When exactly one leftover `prev` name and
   exactly one leftover `curr` name have the same normalized name, they are a renamed pair. When either side has two
   or more leftovers with that normalized name, none of them is renamed. (c) Every other leftover stays a leftover.
4. **Report the matching.** Make one `Drift(kind, column, detail)` per name:
   - each renamed pair: `Drift('renamed', <curr name>, 'was <prev name>')`
   - each leftover `prev` name: `Drift('removed', <prev name>, 'type <prev type>')`
   - each leftover `curr` name: `Drift('added', <curr name>, 'type <curr type>')`
5. **Diff each matched pair.** For every pair from step 3, exact or renamed, check the four rules below. One pair
   can get several drifts. Each one's `column` is the `curr` name.
   - `type_changed` when `prev.type != curr.type` (int -> float counts). Detail: `'<prev type> -> <curr type>'`,
     e.g. `'float -> string'`.
   - `date_format_changed` when `prev.type == curr.type` and `prev.fmt != curr.fmt`, so never together with
     `type_changed`. Detail: `'<prev fmt> -> <curr fmt>'`.
   - `fill_rate_drop` when `round(prev.fill_rate - curr.fill_rate, 4) > FILL_DROP_THRESHOLD` (0.20). Exactly 0.20
     is not a drop, and a rise never is. Detail: `'<prev fill_rate> -> <curr fill_rate>'`, e.g. `'1.0 -> 0.6667'`.
   - `new_values` when `prev.categories` and `curr.categories` are both not `None` and
     `curr.categories - prev.categories` is not empty. Detail: those new values, sorted, joined with `', '`.

   Column position is never compared: a column that only moved is not drift. `detail` is free text for humans: the
   tests only check that a `renamed` detail contains the old name and a `new_values` detail contains each new value.
   Use the detail strings above so your report matches the Example.
6. **Sort and return.** Sort the step 4 and step 5 drifts by (`kind`, `column`), plain string order (uppercase
   letters sort before lowercase ones, so `'CollectedAt'` comes before `'collected-at'`). Return the list.
7. **Write the report.** If `paths` has fewer than two paths, raise `ValueError`. Profile each file with
   `infer_schema`, then `compare` each consecutive pair: `paths[0]` with `paths[1]`, `paths[1]` with `paths[2]`,
   and so on. Return these lines, joined with `"\n"`, plus one `"\n"` at the end:
   - `# Schema drift report`
   - then, for each pair in order:
     - an empty line
     - `## <prev file name> -> <curr file name>`, using base names (`Path(p).name`), e.g.
       `## site_x_2024Q1.csv -> site_x_2024Q2.csv`
     - an empty line
     - if `compare` returned an empty list: `No drift.`
     - otherwise: `| kind | column | detail |`, then `|---|---|---|`, then one line
       `| {kind} | {column} | {detail} |` per `Drift`, in `compare`'s order.

## Output

| function | returns |
|---|---|
| `normalize_name(name)` | `str`: the name lowercased, keeping only `a`-`z` and `0`-`9` (step 3) |
| `infer_type(values)` | `tuple[str, str or None]`: `(type, fmt)` (step 1) |
| `infer_schema(path)` | `dict[str, ColumnInfo]`: one profile per column, keys in header order (step 2) |
| `compare(prev, curr)` | `list[Drift]`, sorted by (`kind`, `column`) (steps 3-6); `[]` when nothing drifted |
| `drift_report(paths)` | `str`: the Markdown report (step 7) |

Dataclass: `Drift` (in `solution.py`), one change between two profiles

| field | type | notes |
|---|---|---|
| kind | str | `added`, `removed`, `renamed`, `type_changed`, `date_format_changed`, `fill_rate_drop` or `new_values` |
| column | str | the `curr` name; the `prev` name for `removed` |
| detail | str | the detail string from step 4 or step 5 |

## Example

Try it on your code (inputs editable): `python tasks.py try data 04`.

Input file `lab_a.csv` (6 data rows; row 3's age is `" 45 "`, with spaces):

```text
patient_id,collected_at,age,value,unit,note
P001,2024-01-02 08:00:00,34,95,mg/dL,fasting
P002,2024-01-03 09:30:00,51,6.1,%,
P003,2024-01-04 10:00:00, 45 ,110,mg/dL,repeat
P004,2024-01-05 11:15:00,29,5.8,%,fasting
P005,2024-01-06 12:00:00,62,102,mg/dL,
P006,2024-01-07 13:45:00,38,7.2,%,fasting
```

Input file `lab_b.csv` (the same 6 patients, next quarter):

```text
patient_id,age,CollectedAt,value,unit,clinic
P001,34,2024-01-02 08:00:00,95,mg/dL,C1
P002,51,2024-01-03 09:30:00,43,mmol/mol,C2
P003,,2024-01-04 10:00:00,110,mg/dL,C1
P004,29,2024-01-05 11:15:00,5.8,%,C2
P005,,2024-01-06 12:00:00,<5,mg/dL,C1
P006,38,2024-01-07 13:45:00,7.2,%,C1
```

`infer_schema("lab_a.csv")` (categories shown sorted):

```text
+--------------+----------+-------------------+-----------+---------------------------------------+
| name         | type     | fmt               | fill_rate | categories                            |
+--------------+----------+-------------------+-----------+---------------------------------------+
| patient_id   | string   | None              | 1.0       | {P001, P002, P003, P004, P005, P006}  |
| collected_at | datetime | %Y-%m-%d %H:%M:%S | 1.0       | {the 6 collected_at values}           |
| age          | int      | None              | 1.0       | {29, 34, 38, 45, 51, 62}              |
| value        | float    | None              | 1.0       | {102, 110, 5.8, 6.1, 7.2, 95}         |
| unit         | string   | None              | 1.0       | {%, mg/dL}                            |
| note         | string   | None              | 0.6667    | {fasting, repeat}                     |
+--------------+----------+-------------------+-----------+---------------------------------------+
```

`print(drift_report(["lab_a.csv", "lab_b.csv"]))`:

```text
# Schema drift report

## lab_a.csv -> lab_b.csv

| kind | column | detail |
|---|---|---|
| added | clinic | type string |
| fill_rate_drop | age | 1.0 -> 0.6667 |
| new_values | unit | mmol/mol |
| new_values | value | 43, <5 |
| removed | note | type string |
| renamed | CollectedAt | was collected_at |
| type_changed | value | float -> string |
```

`drift_report(["lab_a.csv", "lab_a.csv"])` returns `'# Schema drift report\n\n## lab_a.csv -> lab_a.csv\n\nNo drift.\n'`.

`compare` on hand-built profiles (`ColumnInfo` fields: name, type, fmt, fill_rate, categories):

```python
prev = {
    "collected_at": ColumnInfo("collected_at", "date", "%Y-%m-%d", 1.0, None),
    "drawn": ColumnInfo("drawn", "date", "%Y-%m-%d", 1.0, None),
    "dob": ColumnInfo("dob", "date", "%Y-%m-%d", 1.0, None),
    "flag": ColumnInfo("flag", "string", None, 0.9, frozenset({"H", "L"})),
    "site": ColumnInfo("site", "string", None, 0.95, None),
}
curr = {
    "CollectedAt": ColumnInfo("CollectedAt", "date", "%Y-%m-%d", 1.0, None),
    "collected-at": ColumnInfo("collected-at", "date", "%Y-%m-%d", 1.0, None),
    "drawn": ColumnInfo("drawn", "date", "%m/%d/%Y", 1.0, None),
    "dob": ColumnInfo("dob", "string", None, 1.0, None),
    "flag": ColumnInfo("flag", "string", None, 0.7, frozenset({"H", "L", "LL"})),
    "site": ColumnInfo("site", "string", None, 0.6, frozenset({"S01", "S02"})),
}
```

```python
>>> for d in compare(prev, curr): print(d)
Drift(kind='added', column='CollectedAt', detail='type date')
Drift(kind='added', column='collected-at', detail='type date')
Drift(kind='date_format_changed', column='drawn', detail='%Y-%m-%d -> %m/%d/%Y')
Drift(kind='fill_rate_drop', column='site', detail='0.95 -> 0.6')
Drift(kind='new_values', column='flag', detail='LL')
Drift(kind='removed', column='collected_at', detail='type date')
Drift(kind='type_changed', column='dob', detail='date -> string')
```

A few more `infer_type` calls:

```python
>>> infer_type([" 7 ", "8", ""])
('int', None)
>>> infer_type(["1e3", ".5", "-2."])
('float', None)
>>> infer_type(["nan", "1.0"])
('string', None)
>>> infer_type(["01/02/2024", "12/31/2024"])
('date', '%m/%d/%Y')
>>> infer_type(["2024-01-02", "2024-01-02 08:00:00"])
('string', None)
>>> infer_type(["", "  "])
('string', None)
```

Explanation:

- **Step 1.** In `lab_a.csv`, `age` is int (`" 45 "` is stripped first), and `value` mixes `95` and `6.1`, so it is
  float. `collected_at` fails both date formats (`strptime` rejects the time part), and the first datetime format
  fits every value. In `lab_b.csv`, `value` holds `<5`, which matches neither number regex, so it is string. In the
  extra calls, `nan` is not a number, and a column whose values are all empty is string.
- **Step 2.** `note` has 4 non-empty values out of 6 rows: round(4 / 6, 4) = `0.6667`. With only 6 rows, every
  column has at most 20 distinct values, so every column keeps `categories`. In the real quarterly files, columns
  like `patient_id` have more than 20 distinct values and get `None`.
- **Step 3.** `patient_id`, `age`, `value` and `unit` match by exact name. `collected_at` and `CollectedAt` are the
  only leftovers that normalize to `collectedat`, so they are a renamed pair. In the hand-built `compare`, both
  `CollectedAt` and `collected-at` normalize to `collectedat`: two names on the `curr` side, so there is no rename.
- **Step 4.** File pair: `CollectedAt` is `renamed` (`was collected_at`), `note` is `removed` and `clinic` is
  `added`. Hand-built pair: the ambiguous names give `added` twice and `removed` once.
- **Step 5.** File pair: `value` went from float to string (`type_changed`), and its new values `43` and `<5` are
  also `new_values`, because both sides kept `categories`. `unit` gained `mmol/mol`. `age`'s fill rate fell from
  1.0 to 0.6667 (2 of 6 empty): round(1.0 - 0.6667, 4) = 0.3333 > 0.20. `age` also moved position, which is not
  drift, and its remaining values are all old ones. The renamed `CollectedAt` has the same type, format and values,
  so the rename is its only drift. Hand-built pair: `drawn` keeps type date with a new format
  (`date_format_changed`). `dob` changed type, so its format change is not reported. `flag` fell from 0.9 to 0.7:
  `0.9 - 0.7` is `0.20000000000000007`, and round(..., 4) = 0.2 is not > 0.20, so no drop. `flag` gained `LL`.
  `site` fell 0.35 (`fill_rate_drop`), and its `prev.categories` is `None`, so it has no `new_values`.
- **Step 6.** Sorted by `kind`, then `column`: `added` < `date_format_changed` < `fill_rate_drop` < `new_values` <
  `removed` < `renamed` < `type_changed`, and within `added`, `CollectedAt` comes before `collected-at`.
- **Step 7.** One pair of files gives one `##` section. With drift, the section is the table; comparing a file
  with itself gives `No drift.` instead.

## Implement (in `solution.py`)

```python
def normalize_name(name: str) -> str
def infer_type(values: list[str]) -> tuple[str, str | None]
def infer_schema(path) -> dict[str, ColumnInfo]
def compare(prev, curr) -> list[Drift]
def drift_report(paths) -> str
```

The dataclasses and constants in `solution.py` are part of the spec: use them as given.

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
- **Pedestal mapping:** this is the gate in Step Functions before the Glue job writes. Glue crawlers and Iceberg schema evolution will happily *accept* an added column or a widened type, so silent acceptance is the risk. Renames are the dangerous one: Iceberg tracks columns by ID, but a site renaming a CSV header looks like drop + add, and silver gets nulls. A per-site column map (site column name to standard field) is where a confirmed rename gets fixed. Fill-rate and new-value checks become dbt tests (`not_null` with thresholds, `accepted_values`) in bronze/silver. A unit change like `%` to `mmol/mol` for HbA1c is a medical plausibility problem, not just a schema one: the same result goes from about 6 (%) to about 42 (mmol/mol).
