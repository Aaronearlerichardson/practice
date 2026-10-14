# 05. Lab unit normalization is the slowest step in the pipeline

**Timebox: 15 min** | Fix: `03_python/debugging/05_lab_unit_normalize/buggy.py`

## Input

Table: `labs`, a pandas DataFrame, for `normalize_labs(labs)`

```text
+-------------+------------+------------------------------------------------+
| Column Name | Type       | Notes                                          |
+-------------+------------+------------------------------------------------+
| lab_id      | str or int | row identifier, e.g. 'L0000001'                |
| test_code   | str        | e.g. 'glucose'; may have stray spaces or       |
|             |            | capitals, e.g. ' Glucose'                      |
| unit        | str        | source unit, e.g. 'mg/dL'                      |
| value       | float      | in the source unit; NaN when missing           |
+-------------+------------+------------------------------------------------+
```

One row per lab result. The index can be any labels, not only 0 to n-1. A
large site's quarterly extract is about 2,000,000 rows.

`plausibility_summary(normalized)` takes the frame that `normalize_labs`
returns.

Two lookup tables are constants in `buggy.py`. `CONVERSIONS` maps a
(test, source unit) pair to its canonical unit and multiplier:

```text
+-------------+--------+----------------+------------+
| test        | unit   | canonical unit | multiplier |
+-------------+--------+----------------+------------+
| glucose     | mg/dL  | mmol/L         | 1 / 18.016 |
| glucose     | mmol/L | mmol/L         | 1.0        |
| creatinine  | mg/dL  | umol/L         | 88.42      |
| creatinine  | umol/L | umol/L         | 1.0        |
| cholesterol | mg/dL  | mmol/L         | 1 / 38.67  |
| cholesterol | mmol/L | mmol/L         | 1.0        |
| hemoglobin  | g/dL   | g/dL           | 1.0        |
| hemoglobin  | g/L    | g/dL           | 0.1        |
| hba1c       | %      | %              | 1.0        |
+-------------+--------+----------------+------------+
```

`PLAUSIBLE_RANGE` gives each test's plausible range in its canonical unit,
both ends included:

```text
+-------------+------+--------+
| test        | low  | high   |
+-------------+------+--------+
| glucose     | 1.0  | 45.0   |
| creatinine  | 10.0 | 2500.0 |
| cholesterol | 1.0  | 20.0   |
| hemoglobin  | 3.0  | 25.0   |
| hba1c       | 3.0  | 20.0   |
+-------------+------+--------+
```

## Ticket (from the pipeline owner)

> In the Step Functions run history, the `normalize_labs` task now takes ~25
> minutes for one large site's quarterly lab extract (~2M rows). Everything
> else in the silver build takes under a minute. The output is correct, and
> the analysts depend on the exact `qc_reason` values, so please don't change
> behavior. Locally, `bench.py` shows ~40-50 us per row no matter the size.

## Task

**Goal:** make `normalize_labs` fast enough for a 2,000,000-row extract while
it returns exactly the frame it returns today: one output row per input row,
with four columns added.

The behavior below must not change. Steps 1-6 are `normalize_labs(labs)`
(steps 2-6 decide the four new columns for each row) and steps 7-8 are
`plausibility_summary(normalized)`.

1. **Copy the input.** Start from a copy of `labs`: the same columns in the
   same order, the same index labels and the same row order. `labs` itself
   is not changed. Add four columns after the input columns, in this order:
   `value_std`, `unit_std`, `plausible`, `qc_reason`.
2. **Clean the lookup key.** `test` = `test_code` as a string, with leading
   and trailing whitespace removed, lower-cased (`' Glucose'` -> `'glucose'`).
   `unit` = `unit` as a string, with leading and trailing whitespace removed.
   Case is kept in `unit`, so `'mg/dl'` does not match `'mg/dL'`.
3. **Look up the conversion.** When (`test`, `unit`) is not a pair in
   `CONVERSIONS`, the row gets `qc_reason = 'unknown_unit'`,
   `unit_std = None`, `value_std = NaN` and `plausible = False`, and steps
   4-6 are skipped. This check comes first: a row with an unknown pair and a
   missing `value` is `'unknown_unit'`.
4. **Check the value.** Otherwise `unit_std` = the pair's canonical unit.
   When `value` is NaN, the row gets `qc_reason = 'missing_value'`,
   `value_std = NaN` and `plausible = False`, and steps 5-6 are skipped.
5. **Convert.** `value_std = value * multiplier`, a float, not rounded.
6. **Check the range.** With (`low`, `high`) = `PLAUSIBLE_RANGE[test]`: when
   `low <= value_std <= high`, the row gets `plausible = True` and
   `qc_reason = ''`. Otherwise it gets `plausible = False` and
   `qc_reason = 'out_of_range'`.
7. **Group by test.** `test` = `test_code` with leading and trailing
   whitespace removed, lower-cased. One output row per distinct `test`,
   including tests that are not in `CONVERSIONS` (such as `'potassium'`).
   The index is named `test` and sorted ascending.
8. **Compute the rates.** `n` = number of rows for that test.
   `fill_rate` = share of those rows whose `value_std` is not NaN.
   `plausible_rate` = share of those rows with `plausible == True`. Both
   rates are rounded to 4 decimals.

**Speed target (tested).** `test_perf_budget` builds 100,000 rows with the
test file's `make_labs(100_000)` (9 (test, unit) pairs, one of them the
unknown `('glucose', 'mg/dl')`, about 3% missing values and about 1% values
x100) and times one `normalize_labs(labs)` call in a separate process. It
must take under 0.5 s; the process is stopped after 5.5 s. `bench.py` times
the production size, 2,000,000 rows in under 5 s. The tests do not run it,
but it is the real goal.

## Output

`normalize_labs(labs)` returns a new DataFrame with the same index as
`labs`:

| column | dtype | notes |
|---|---|---|
| lab_id, test_code, unit, value | unchanged | copied from `labs` as they are (step 1) |
| value_std | float64 | step 5; NaN for `'unknown_unit'` and `'missing_value'` rows |
| unit_std | object | the canonical unit, a `str` (step 4); `None` for `'unknown_unit'` rows |
| plausible | bool | step 6; `True` exactly when `qc_reason == ''` |
| qc_reason | str | `''`, `'unknown_unit'`, `'missing_value'` or `'out_of_range'` (steps 3, 4, 6) |

`plausibility_summary(normalized)` returns a DataFrame with index `test`
(step 7), sorted ascending:

| column | dtype | notes |
|---|---|---|
| n | int64 | number of rows for the test (step 8) |
| fill_rate | float64 | share of rows with `value_std` not NaN, rounded to 4 decimals |
| plausible_rate | float64 | share of rows with `plausible == True`, rounded to 4 decimals |

## Example

Input `labs` (note the index starts at 10, and the quotes show the spaces in
`' Glucose'` and `'mmol/L '`):

```text
+-------+--------+-------------+-----------+-------+
| index | lab_id | test_code   | unit      | value |
+-------+--------+-------------+-----------+-------+
| 10    | L1     | glucose     | mg/dL     | 126.0 |
| 11    | L2     | ' Glucose'  | 'mmol/L ' | 7.1   |
| 12    | L3     | creatinine  | mg/dL     | 1.2   |
| 13    | L4     | hemoglobin  | g/L       | 142.0 |
| 14    | L5     | hba1c       | %         | 25.0  |
| 15    | L6     | hba1c       | %         | 20.0  |
| 16    | L7     | glucose     | mg/dl     | 99.0  |
| 17    | L8     | cholesterol | mg/dL     | NaN   |
| 18    | L9     | potassium   | mmol/L    | NaN   |
+-------+--------+-------------+-----------+-------+
```

Output of `normalize_labs(labs)` (`test_code`, `unit` and `value` are
unchanged and left out here; `value_std` is rounded to 6 decimals for
display):

```text
+-------+--------+-----------+----------+-----------+---------------+
| index | lab_id | value_std | unit_std | plausible | qc_reason     |
+-------+--------+-----------+----------+-----------+---------------+
| 10    | L1     | 6.993783  | mmol/L   | True      | ''            |
| 11    | L2     | 7.1       | mmol/L   | True      | ''            |
| 12    | L3     | 106.104   | umol/L   | True      | ''            |
| 13    | L4     | 14.2      | g/dL     | True      | ''            |
| 14    | L5     | 25.0      | %        | False     | out_of_range  |
| 15    | L6     | 20.0      | %        | True      | ''            |
| 16    | L7     | NaN       | None     | False     | unknown_unit  |
| 17    | L8     | NaN       | mmol/L   | False     | missing_value |
| 18    | L9     | NaN       | None     | False     | unknown_unit  |
+-------+--------+-----------+----------+-----------+---------------+
```

Output of `plausibility_summary(normalize_labs(labs))`:

```text
+-------------+---+-----------+----------------+
| test        | n | fill_rate | plausible_rate |
+-------------+---+-----------+----------------+
| cholesterol | 1 | 0.0       | 0.0            |
| creatinine  | 1 | 1.0       | 1.0            |
| glucose     | 3 | 0.6667    | 0.6667         |
| hba1c       | 2 | 1.0       | 0.5            |
| hemoglobin  | 1 | 1.0       | 1.0            |
| potassium   | 1 | 0.0       | 0.0            |
+-------------+---+-----------+----------------+
```

<details><summary>The same input as Python, for a REPL</summary>

```python
import numpy as np
import pandas as pd

labs = pd.DataFrame({
    "lab_id":    ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"],
    "test_code": ["glucose", " Glucose", "creatinine", "hemoglobin", "hba1c",
                  "hba1c", "glucose", "cholesterol", "potassium"],
    "unit":      ["mg/dL", "mmol/L ", "mg/dL", "g/L", "%", "%", "mg/dl", "mg/dL", "mmol/L"],
    "value":     [126.0, 7.1, 1.2, 142.0, 25.0, 20.0, 99.0, np.nan, np.nan],
}, index=[10, 11, 12, 13, 14, 15, 16, 17, 18])
```

</details>

Explanation:

- **Step 1.** The output keeps index 10 to 18 and the four input columns.
  `labs` still has only its four columns afterwards.
- **Step 2.** L2's `' Glucose'` becomes `'glucose'` and its `'mmol/L '`
  becomes `'mmol/L'`. L7's `'mg/dl'` stays `'mg/dl'`.
- **Step 3.** L7's (`'glucose'`, `'mg/dl'`) is not in `CONVERSIONS`: the
  lower-case `l` does not match. L9's `'potassium'` is not a known test, and
  its value is also missing, but `'unknown_unit'` is checked first.
- **Step 4.** L8 is a known pair, so it gets `unit_std = 'mmol/L'`, but its
  value is NaN: `'missing_value'`.
- **Step 5.** L1: 126 / 18.016 = 6.993783 mmol/L. L3: 1.2 x 88.42 = 106.104
  umol/L. L4: 142 x 0.1 = 14.2 g/dL (the stored float is
  14.200000000000001).
- **Step 6.** L5's 25.0 is above hba1c's high of 20.0: `'out_of_range'`. L6's
  20.0 equals the high end, which is included, so it is plausible.
- **Step 7.** L1, L2 and L7 are all `glucose` after cleaning, so glucose has
  3 rows. `potassium` gets its own row even though it has no conversion.
- **Step 8.** glucose: L1 and L2 have a `value_std`, L7 does not, so
  `fill_rate` = 2 / 3 = 0.6667, and `plausible_rate` = 2 / 3 = 0.6667.
  hba1c: L6 is plausible and L5 is not: 1 / 2 = 0.5.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `normalize_labs` and
  `plausibility_summary`, because the tests import them.
- **Don't edit:** `test_05_lab_unit_normalize.py` and `bench.py`. The tests
  are the spec, so a pass only counts with them unchanged. To poke at the
  data, use a REPL or a scratch file.

## Run

```powershell
python -m pytest 03_python\debugging\05_lab_unit_normalize -q
python 03_python\debugging\05_lab_unit_normalize\bench.py
```

<details><summary>Hints</summary>

1. Time scales linearly but the constant is huge. What does each loop
   iteration create, and what does each `out.at[...]` write cost? Try
   `%prun` or `cProfile` on 20k rows.
2. Do the conversion lookup for all rows at once (a mapping or a reindex on a
   `(test, unit)` table), then compute the reason with boolean masks and
   `np.select`, respecting the precedence order in the docstring.

</details>

## Say out loud

- Reproduce: time per row from `bench.py`; it is constant and large.
- Hypothesize: per-row Python and pandas overhead (`iterrows` + `.at`), not the math.
- Isolate: profile; most time is in Series construction and indexing.
- Fix: columnar lookups and masks; keep the rule precedence explicit.
- Prevent: a golden-output test on a small frame plus a performance budget test.
