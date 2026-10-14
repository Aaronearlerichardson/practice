# 05. Lab unit normalization is the slowest step in the pipeline

**Timebox: 15 min**

## Input

Table: `labs`, a pandas DataFrame, for `normalize_labs(labs)`

```text
+-------------+------------+------------------------------------------------+
| Column Name | Type       | Notes                                          |
+-------------+------------+------------------------------------------------+
| lab_id      | str or int | row identifier, e.g. 'L0000001'                |
| test_code   | str        | e.g. 'glucose'; known tests are in CONVERSIONS |
| unit        | str        | source unit, e.g. 'mg/dL'; see CONVERSIONS     |
| value       | float      | can be missing (NaN)                           |
+-------------+------------+------------------------------------------------+
```

One row per lab result. `CONVERSIONS` maps each known (test, unit) pair to its
canonical unit and multiplier. `PLAUSIBLE_RANGE` gives each test's inclusive
range in the canonical unit. A large site's quarterly extract is about
2,000,000 rows.

`plausibility_summary(normalized)` takes the frame that `normalize_labs`
returns.

## Ticket (from the pipeline owner)

> In the Step Functions run history, the `normalize_labs` task now takes ~25
> minutes for one large site's quarterly lab extract (~2M rows). Everything
> else in the silver build takes under a minute. The output is correct, and
> the analysts depend on the exact `qc_reason` values, so please don't change
> behavior. Locally, `bench.py` shows ~40-50 us per row no matter the size.

Make `normalize_labs` fast (target: 2M rows in a few seconds) with identical
output: same `value_std`, `unit_std`, `plausible`, `qc_reason`, same index,
and the input frame must not be modified.

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
