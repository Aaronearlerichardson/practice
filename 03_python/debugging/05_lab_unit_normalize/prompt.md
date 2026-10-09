# 05. Lab unit normalization is the slowest step in the pipeline

**Timebox: 15 min**

## Ticket (from the pipeline owner)

> In the Step Functions run history, the `normalize_labs` task now takes ~25
> minutes for one large site's quarterly lab extract (~2M rows). Everything
> else in the silver build takes under a minute. The output is correct, and
> the analysts depend on the exact `qc_reason` values, so please don't change
> behavior. Locally, `bench.py` shows ~40-50 us per row no matter the size.

Make `normalize_labs` fast (target: 2M rows in a few seconds) with identical
output: same `value_std`, `unit_std`, `plausible`, `qc_reason`, same index,
and the input frame must not be modified.

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
