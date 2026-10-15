# 03. Two gigabytes, ten megabytes

**Timebox: 35 min** | Write: `03_python/data_tasks/03_streaming_aggregates/solution.py`

## Input

Argument: `in_path`, the path of one lab extract, for `summarize(in_path, summary_path, rejects_path)`.

File: the CSV at `in_path` (comma-separated, header row, standard CSV quoting)

```text
+----------------+------+-------------------------------------------------+
| Column Name    | Type | Notes                                           |
+----------------+------+-------------------------------------------------+
| row_id         | text | integer row number, e.g. '17'                   |
| site_id        | text | e.g. 'S01'; can have spaces around it (' S02')  |
| patient_id     | text | e.g. 'P000001'                                  |
| test_code      | text | e.g. 'GLU'; can be lowercase or padded (' glu') |
| collected_date | text | ISO YYYY-MM-DD                                  |
| value          | text | raw text, e.g. '4.83', ' 4.5 ', '1e2', 'NaN'    |
| unit           | text | e.g. 'mg/dL'                                    |
+----------------+------+-------------------------------------------------+
```

Every value arrives as text. You may assume every line has 7 fields.

Constant: `PLAUSIBLE` in `solution.py`, a `dict[str, tuple[float, float]]` of `test_code -> (low, high)`. Both
ends of each range are plausible. A `test_code` that is not a key here is unknown.

```text
+-----------+-------+--------+
| test_code | low   | high   |
+-----------+-------+--------+
| GLU       | 10.0  | 1000.0 |
| HBA1C     | 2.0   | 20.0   |
| K         | 1.5   | 10.0   |
| NA        | 100.0 | 180.0  |
| HGB       | 2.0   | 25.0   |
| CREAT     | 0.1   | 20.0   |
+-----------+-------+--------+
```

Other arguments:

- `summary_path`, `rejects_path` (for `summarize`): where to write the summary CSV and the rejects CSV.
- `test_code`, `value` (both `str`) for `classify(test_code, value)`: `test_code` is already normalized (stripped
  and uppercased). `value` is the raw text from the file.

Files to work with:

- `data/labs_sample.csv`: 300 rows (the first 16 are handcrafted traps). Use it while you develop.
- `python gen_data.py --size-mb 2000` (from this folder) writes `data/big/labs_big.csv` (gitignored).
  `python tasks.py gen-data --big-mb 2000` does the same from the repo root. Start with 200.

A site's quarterly lab extract is 2 GB, and the container that profiles it has far less memory than that to spare.
In **one pass** and **constant memory**, compute per-(site, test) stats for the quality dashboard, and stream every
invalid row to a rejects file as you go.

## Task

**Goal:** write one summary row per (`site_id`, `test_code`) group with the count, mean, min and max of its valid
values and the number of invalid rows, write every invalid row to a rejects file with a reason, and return three
row counts.

Steps 1-3 are `classify(test_code, value)`. Steps 4-9 are `summarize(in_path, summary_path, rejects_path)`.

1. **Check the test code.** If `test_code` is not a key of `PLAUSIBLE`, return `(None, 'unknown_test')`. This check
   runs first, so `classify('LDL', 'abc')` is `(None, 'unknown_test')`.
2. **Parse the value.** Strip `value` and parse it with `float()`. If `float()` raises `ValueError`, or the result
   is not finite (`math.isfinite` is False: `nan`, `inf`, `-inf` in any case), return `(None, 'non_numeric')`.
   `'1e2'` parses to `100.0`, and `''` is `non_numeric`.
3. **Check the range.** With `(low, high) = PLAUSIBLE[test_code]` and `x` the parsed float, return
   `(None, 'implausible')` unless `low <= x <= high`. Otherwise return `(x, None)`.
4. **Read the rows in one pass.** Open `in_path`, skip the header row, and read the data rows one at a time in file
   order. `rows_read` counts every data row.
5. **Find the row's group.** The group key is (`site_id.strip()`, `test_code.strip().upper()`). Every row belongs to
   its group, valid or not, including rows whose code is unknown (`'LDL'`, `'XYZ'`). A new group starts with
   `count` 0, `invalid_count` 0, and no sum, min or max yet.
6. **Classify the row.** Call `classify(test_code.strip().upper(), value)` with the raw `value`.
7. **Invalid row: write the reject now.** When step 6 returns a reason, add 1 to the group's `invalid_count` and to
   `invalid`, and write one row to the rejects CSV right away: the row's 7 fields exactly as read (not stripped, not
   uppercased), then the reason.
8. **Valid row: update the group's totals.** Otherwise add 1 to the group's `count` and to `valid`, add `x` to the
   group's sum, and update its min and max.
9. **Write the summary and return.** After the last row, write one summary row per group, sorted by the group's
   `site_id`, then `test_code` (plain string order). `mean` = sum / `count`, written with exactly 4 decimals
   (`f"{mean:.4f}"`). A group with `count` 0 writes `mean`, `min` and `max` as empty strings. Return
   `{"rows_read": ..., "valid": ..., "invalid": ...}`.

**Memory:** memory must not grow with the file. Steps 4-8 hold only the current row and one small set of totals per
group: no list of rows and no list of rejects. The test traces peak Python allocations while `summarize` reads a
~30 MB generated file and requires **under 8 MB**.

## Output

| function | returns |
|---|---|
| `classify(test_code, value)` | a 2-tuple: `(x, None)` for a valid value (`x` is the parsed float), `(None, reason)` otherwise |
| `summarize(in_path, summary_path, rejects_path)` | `dict[str, int]`: `rows_read` (step 4), `valid` (step 8), `invalid` (step 7); it also writes the two files below |

Summary CSV at `summary_path`: a header row, then one row per group (step 9), sorted by `site_id`, then
`test_code`. Columns in this order (`SUMMARY_COLUMNS`):

| # | column | notes |
|---|---|---|
| 1 | site_id | group key: `site_id.strip()` |
| 2 | test_code | group key: `test_code.strip().upper()` |
| 3 | count | number of valid rows in the group (step 8) |
| 4 | invalid_count | number of invalid rows in the group (step 7) |
| 5 | mean | sum of the valid values / `count`, as `f"{mean:.4f}"`; `""` when `count` is 0 |
| 6 | min | smallest valid value, as any text that parses back to the same float (e.g. `10.0`); `""` when `count` is 0 |
| 7 | max | largest valid value, same format as `min`; `""` when `count` is 0 |

Rejects CSV at `rejects_path`: a header row, then one row per invalid row, in input order. Columns in this order
(`REJECT_COLUMNS`):

| # | column | notes |
|---|---|---|
| 1-7 | row_id, site_id, patient_id, test_code, collected_date, value, unit | the input fields exactly as read |
| 8 | reason | the reason from step 6: `unknown_test`, `non_numeric` or `implausible` |

## Example

Try it on your code (inputs editable): `python tasks.py try data 03`.

Input file:

```text
row_id,site_id,patient_id,test_code,collected_date,value,unit
1,S01,P000001,GLU,2024-02-01,100,mg/dL
2,S01,P000002," glu",2024-02-02,1e2,mg/dL
3,S01,P000003,GLU,2024-02-03,1000,mg/dL
4,S01,P000004,GLU,2024-02-04,1000.01,mg/dL
5,S01,P000005,GLU,2024-02-05,NaN,mg/dL
6,S01,P000006,K,2024-02-06," 4.5 ",mmol/L
7,S01,P000007,K,2024-02-07,inf,mmol/L
8,S01,P000008,K,2024-02-08,,mmol/L
9," S02",P000009,hba1c,2024-02-09,2,%
10,S02,P000010,LDL,2024-02-10,abc,mg/dL
11,S03,P000011,creat,2024-02-11,-1,mg/dL
12,S01,P000012,GLU,2024-02-12,10,mg/dL
```

Return value:

```python
{'rows_read': 12, 'valid': 6, 'invalid': 6}
```

Summary CSV:

```text
site_id,test_code,count,invalid_count,mean,min,max
S01,GLU,4,2,302.5000,10.0,1000.0
S01,K,1,2,4.5000,4.5,4.5
S02,HBA1C,1,0,2.0000,2.0,2.0
S02,LDL,0,1,,,
S03,CREAT,0,1,,,
```

Rejects CSV:

```text
row_id,site_id,patient_id,test_code,collected_date,value,unit,reason
4,S01,P000004,GLU,2024-02-04,1000.01,mg/dL,implausible
5,S01,P000005,GLU,2024-02-05,NaN,mg/dL,non_numeric
7,S01,P000007,K,2024-02-07,inf,mmol/L,non_numeric
8,S01,P000008,K,2024-02-08,,mmol/L,non_numeric
10,S02,P000010,LDL,2024-02-10,abc,mg/dL,unknown_test
11,S03,P000011,creat,2024-02-11,-1,mg/dL,implausible
```

Explanation:

- **Step 1.** Row 10's code `LDL` is not in `PLAUSIBLE`, so it is `unknown_test`, even though its value `abc` is
  not a number either.
- **Step 2.** Row 2's `1e2` parses to 100.0 and row 6's `' 4.5 '` parses to 4.5 after stripping. Rows 5 (`NaN`)
  and 7 (`inf`) parse with `float()` but are not finite, and row 8's empty value does not parse: all three are
  `non_numeric`.
- **Step 3.** Rows 3 (1000) and 12 (10) sit exactly on GLU's bounds and are valid. Row 4 (1000.01) and row 11 (-1,
  below CREAT's 0.1) are `implausible`.
- **Step 4.** 12 data rows after the header, so `rows_read` is 12.
- **Step 5.** Row 2's `' glu'` joins `S01,GLU`. Row 9's `' S02'` and `hba1c` make the key (`S02`, `HBA1C`). Row
  11's `creat` makes (`S03`, `CREAT`).
- **Step 6.** Each row is classified with its normalized code: row 11 is checked as `CREAT`.
- **Step 7.** The 6 invalid rows go to rejects in input order, with their raw fields: row 8's value stays empty and
  row 11's code stays `creat`.
- **Step 8.** `S01,GLU` keeps 100, 100, 1000 and 10: `count` 4, min 10.0, max 1000.0.
- **Step 9.** `S01,GLU` mean = 1210 / 4 = `302.5000`. `S02,LDL` and `S03,CREAT` have no valid rows, so they still
  appear, with `count` 0 and empty `mean`, `min` and `max`. Rows are sorted by `site_id`, then `test_code`.

## Implement (in `solution.py`)

```python
def classify(test_code: str, value: str) -> tuple[float | None, str | None]
def summarize(in_path, summary_path, rejects_path) -> dict[str, int]   # rows_read, valid, invalid
```

## Run the tests (PowerShell, from the repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest 03_python\data_tasks\03_streaming_aggregates -q -p no:cacheprovider
```

The memory test generates a 30 MB file in a temp dir, so the run takes 10-30 s.

<details><summary>Hints</summary>

- `csv.reader` over an open file is already a stream. Keep a dict of `group -> [count, sum, min, max, invalid]` and write each reject the moment you see it.
- Memory is O(groups), not O(rows). The generated file has 12 sites x 7 codes (the 6 tests plus `LDL`), so 84 entries.
- `float("1e2")` is 100 and is valid. `float("nan")` and `float("inf")` succeed, so check `math.isfinite`.
- pandas works if you use `chunksize` with `dtype=str, keep_default_na=False`, and keep chunks around 20-50k rows.
- Don't collect the rejects in a list and write them at the end.

</details>

<details><summary>Check yourself</summary>

On `data/labs_sample.csv`:

- `{"rows_read": 300, "valid": 288, "invalid": 12}`. Rejects by reason: `implausible` 6, `non_numeric` 4, `unknown_test` 2.
- **74** summary rows. Two have `count` 0: `S02,XYZ` and `S12,LDL`.
- `S01,GLU`: count 16, invalid 2, mean `290.7981`, min 10.0, max 1000.0 (both bounds are inclusive).
- Row 11 has site `" S02"` and row 12 has code `hba1c`: both land in `S02,HBA1C`.

On a generated file: `sum(count) + sum(invalid_count)` equals the number of rows the generator wrote. If it doesn't, you lost rows.

</details>

## Say it out loud

- **Restate:** one sequential pass, O(groups) memory, and every row is accounted for in exactly one group, valid or invalid.
- **Edge cases:** NaN and inf parse as floats, scientific notation, padded values, inclusive bounds, codes in mixed case, a group with no valid rows, unknown codes.
- **Plan:** a running count/sum/min/max per group, rejects written as they stream, the summary written at the end from the small dict.
- **Complexity:** O(n) time, O(g) memory for g groups, plus a constant-size read buffer.
- **Numerics:** a naive sum over billions of rows loses precision. Use `math.fsum` per chunk, Kahan summation, or Welford's algorithm, which also gives you variance in one pass.
- **Median:** an exact median can't be computed in one pass with constant memory (you'd need every value, or a second pass). Options: t-digest or KLL sketches (approximate, mergeable), a fixed-bin histogram over the plausible range (exact counts per bin, approximate within a bin), or an exact answer with a second pass or an external sort. Say which error you can accept.
- **At 100x (200 GB):** split by byte ranges or by file and aggregate per partition. count/sum/min/max (and t-digests) merge associatively, so a map-reduce gives exactly the same answer.
- **Pedestal mapping:** this is the profiling step that feeds quality checks (fill rates, plausibility ranges) before bronze-to-silver. In Glue or Spark it's a `groupBy(site_id, test_code).agg(...)` with `percentile_approx` for the median, which is a sketch, not exact. In dbt it's a test or a model over the Iceberg table, and the plausibility table belongs in a seed so clinicians can review it.
- **Caveat on the test:** tracemalloc only sees Python allocations. pyarrow-backed pandas strings live outside it, so "< 8 MB traced" is a guardrail, not proof. In production you'd watch the container's RSS.
