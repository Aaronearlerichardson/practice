# 06. Lab profiling job runs out of memory

**Timebox: 12 min** | Fix: `03_python/debugging/06_lab_extract_memory/buggy.py`

## Input

File: one site's quarterly lab extract, passed as `path` to
`summarize_lab_extract(path, delimiter)`. UTF-8, with a header row.

```text
+---------------+------+----------------------------------------------------------------+
| Column Name   | Type | Notes                                                          |
+---------------+------+----------------------------------------------------------------+
| patient_id    | text | e.g. 'P0000001'                                                |
| site_id       | text | e.g. 'S07'                                                     |
| test_code     | text | e.g. 'GLU'                                                     |
| value         | text | can be blank (missing) or non-numeric, e.g. '<0.5', 'see note' |
|               |      | and can have spaces around it, e.g. ' 0.9 '                    |
| unit          | text | e.g. 'mg/dL'                                                   |
| drawn_at      | text | ISO timestamp, e.g. '2026-07-01T08:00:00'                      |
| result_status | text | e.g. 'final', 'corrected', 'cancelled'                         |
+---------------+------+----------------------------------------------------------------+
```

One row per lab result. Line 1 is the header with these seven column names,
and every other non-blank line has all seven fields. Sites deliver one file
per quarter, and a large site's file can be several GB.

Other arguments:

- `delimiter` (`str`): the field separator. Defaults to `","`. A TSV
  delivery passes `"\t"`.

## Ticket (from the platform team)

> The bronze profiling job for site S07 failed again with
> `MemoryError` / container OOM-killed on the Glue worker. S07's Q3 lab
> extract is 9 GB. Smaller sites are fine. We bumped the worker size once
> already and it just moved the failure to the next bigger file. The job only
> produces a tiny per-test summary (a dozen numbers per test code), so it is
> strange that it needs memory proportional to the file.

## Task

**Goal:** fix `buggy.py` so that `summarize_lab_extract` returns exactly the
summary it returns today (one entry per `test_code`), while its peak memory
stays under 8 MB however big the file is.

The fixed code runs these steps. Steps 1-5 are `summarize_lab_extract(path,
delimiter)`. Step 6 is its helper `_finalize`, called once per `test_code`.

1. **Read the header.** Split line 1 on `delimiter`, with standard CSV
   quoting, and find the `test_code`, `value` and `result_status` columns by
   name.
2. **Read the data rows.** Split every later line the same way. Skip a blank
   line. Skip a row whose `result_status` is exactly `'cancelled'`. Rows with
   any other status, such as `'final'` or `'corrected'`, are kept.
3. **Count the row.** Add 1 to `n` for the row's `test_code`, taken as is. A
   `test_code` seen for the first time starts with every count at 0.
4. **Classify `value`.** Strip spaces from both ends. If the result is `""`,
   add 1 to `n_missing`. Otherwise, if Python's `float()` accepts it (for
   example `'140.5'` or `'0.9'`), it is numeric. Otherwise (for example
   `'<0.5'` or `'see note'`), add 1 to `n_nonnumeric`.
5. **Track the numeric values.** For each numeric value, add it to the
   `test_code`'s running sum, and update its smallest and largest value.
6. **Finish each test code.** After the last row, for each `test_code`:
   `n_numeric = n - n_missing - n_nonnumeric`,
   `fill_rate = round(n_numeric / n, 4)`,
   `mean = round(sum / n_numeric, 4)`, and `min` and `max` are the smallest
   and largest numeric values, not rounded. When `n_numeric` is 0, `mean`,
   `min` and `max` are `None`. Return one entry per `test_code` that has at
   least one kept row, in ascending `test_code` order.

**Memory budget (what the tests measure).** `test_peak_memory_budget` writes
a synthetic CSV of about 25 MB (at least 25 x 1024 x 1024 bytes, five test
codes), starts `tracemalloc`, calls `summarize_lab_extract(path)` once, and
requires the peak of traced Python allocations to be under **8.0 MB**. The
buggy code peaks at about 72.6 MB on that file. `bench.py` checks the same
8.0 MB budget on files of 5, 10, 25, 50 and 100 MB, so peak memory must not
grow with file size. On the same 25 MB file, `test_big_file_reconciles`
checks that the keys are exactly `'A1C'`, `'CREAT'`, `'GLU'`, `'HGB'` and
`'K'`, and that the `n` values add up to the file's non-cancelled rows.

## Output

`summarize_lab_extract(path, delimiter)` returns a `dict[str, dict]`:
`test_code` -> the dict below, with keys in ascending `test_code` order.

| key | type | notes |
|---|---|---|
| n | int | step 3: kept rows with this `test_code` |
| n_missing | int | step 4: kept rows whose stripped `value` is `""` |
| n_nonnumeric | int | step 4: kept rows whose stripped `value` is not `""` and `float()` rejects |
| n_numeric | int | step 6: `n - n_missing - n_nonnumeric` |
| fill_rate | float | step 6: `round(n_numeric / n, 4)` |
| mean | float or None | step 6: `round(sum of numeric values / n_numeric, 4)`; `None` when `n_numeric` is 0 |
| min | float or None | step 6: smallest numeric value; `None` when `n_numeric` is 0 |
| max | float or None | step 6: largest numeric value; `None` when `n_numeric` is 0 |

## Example

Input file `S07_labs_small.csv` (row P6's value is `' 0.9 '`, with a space
on each side):

```text
patient_id,site_id,test_code,value,unit,drawn_at,result_status
P1,S07,GLU,100,mg/dL,2026-07-01T08:00:00,final
P2,S07,GLU,,mg/dL,2026-07-01T08:05:00,final
P3,S07,GLU,140.5,mg/dL,2026-07-01T08:10:00,corrected
P4,S07,GLU,999,mg/dL,2026-07-01T08:15:00,cancelled
P5,S07,CREAT,<0.5,mg/dL,2026-07-01T08:20:00,final
P6,S07,CREAT, 0.9 ,mg/dL,2026-07-01T08:25:00,final
P7,S07,K,see note,mmol/L,2026-07-01T08:30:00,final
P8,S07,K,,mmol/L,2026-07-01T08:35:00,final
P9,S07,HGB,13.1,g/dL,2026-07-01T08:40:00,cancelled
```

`S07_labs_small.tsv` holds the same rows with tabs in place of commas.

Output:

```python
>>> summarize_lab_extract("S07_labs_small.csv")
{'CREAT': {'n': 2, 'n_missing': 0, 'n_nonnumeric': 1, 'n_numeric': 1,
           'fill_rate': 0.5, 'mean': 0.9, 'min': 0.9, 'max': 0.9},
 'GLU': {'n': 3, 'n_missing': 1, 'n_nonnumeric': 0, 'n_numeric': 2,
         'fill_rate': 0.6667, 'mean': 120.25, 'min': 100.0, 'max': 140.5},
 'K': {'n': 2, 'n_missing': 1, 'n_nonnumeric': 1, 'n_numeric': 0,
       'fill_rate': 0.0, 'mean': None, 'min': None, 'max': None}}
>>> summarize_lab_extract("S07_labs_small.tsv", delimiter="\t") == summarize_lab_extract("S07_labs_small.csv")
True
```

Explanation:

- **Step 1.** The header names the columns, so `test_code`, `value` and
  `result_status` are found by name. The TSV file gives the same answer
  because only the delimiter differs.
- **Step 2.** P4 (`'cancelled'`) is skipped, so its 999 never reaches GLU's
  `max`. P9 is HGB's only row and it is cancelled, so HGB is not in the
  output at all. P3 is `'corrected'`, so it is kept.
- **Step 3.** GLU has 3 kept rows (P1, P2, P3), CREAT 2 (P5, P6), K 2 (P7,
  P8).
- **Step 4.** P2 and P8 are blank: missing. P5's `'<0.5'` and P7's
  `'see note'` are non-numeric. P6's `' 0.9 '` strips to `'0.9'`, which is
  numeric.
- **Step 5.** GLU's numeric values are 100 and 140.5: sum 240.5, smallest
  100.0, largest 140.5.
- **Step 6.** GLU: `n_numeric` = 3 - 1 - 0 = 2, `fill_rate` =
  round(2 / 3, 4) = 0.6667, `mean` = round(240.5 / 2, 4) = 120.25. K has no
  numeric values, so its `fill_rate` is 0.0 and `mean`, `min` and `max` are
  `None`. The keys come out sorted: CREAT, GLU, K.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of
  `summarize_lab_extract`, because the tests import them.
- **Don't edit:** `test_06_lab_extract_memory.py` and `bench.py`. The tests
  are the spec, so a pass only counts with them unchanged. To poke at the
  data, use a REPL or a scratch file.

## Run

```powershell
python -m pytest 03_python\debugging\06_lab_extract_memory -q
python 03_python\debugging\06_lab_extract_memory\bench.py
```

The tests generate a ~25 MB file in a temp directory and measure peak Python
allocations with `tracemalloc`.

<details><summary>Hints</summary>

1. `bench.py` shows peak memory at about 3x the file size (about 15 MB for
   the 5 MB file), and stops there because that is already over budget.
   What objects exist at the moment of the peak? (Hint: two copies of the
   file's text.)
2. A file object is already an iterator over lines, and `csv.reader` accepts
   any iterable of lines.

</details>

## Say out loud

- Reproduce: peak memory vs file size from `bench.py`.
- Hypothesize: the whole file (plus a list of every line) is materialized.
- Isolate: `tracemalloc` snapshot or reasoning about `read()` + `splitlines()`.
- Fix: stream rows; only the per-test accumulators stay in memory.
- Prevent: a memory-budget test, review rule against `.read()` / `list(reader)`
  on unbounded inputs; for pandas use `chunksize=` or `pyarrow.dataset` scans.
