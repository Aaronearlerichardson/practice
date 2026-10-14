# 03. Encounter dedup step is timing out

**Timebox: 10 min**

## Input

Argument: `rows`, a `list[dict]`, for `dedupe_encounters(rows, key_fields)`
and `dedupe_report(rows)`.

```text
+--------------+------+-------------------------------------------+
| Key          | Type | Notes                                     |
+--------------+------+-------------------------------------------+
| site_id      | str  | key field, e.g. 'S01'                     |
| patient_id   | str  | key field, e.g. 'P0000001'                |
| encounter_id | str  | key field, e.g. 'E00000001'               |
| source_file  | str  | delivery file name; added by read_batches |
+--------------+------+-------------------------------------------+
```

One dict per encounter row, in delivery order (earliest delivery first).
Whitespace and case in the key fields are not significant. A large site
sends about 1,000,000 rows per quarter.

Other arguments:

- `key_fields` (`tuple[str, ...]`): defaults to `KEY_FIELDS`,
  `("site_id", "patient_id", "encounter_id")`.
- `paths` for `read_batches(paths)`: CSV paths in delivery order. Each file
  is UTF-8 with a header row that includes the key fields.

## Ticket (from the on-call data engineer)

> The `dedupe_encounters` Glue job used to finish in seconds. Since the large
> academic site (S07) joined, it has been running for hours, and last night it
> hit the 2-hour task timeout in Step Functions. The output is correct when it
> does finish. Volume went from ~20k encounters per quarter to ~1M.
>
> Local repro: `bench.py` shows 10k rows taking under a second, 20k taking
> about 4x longer, 40k about 4x longer again.

Make it fast enough for 1M rows in a few seconds **without changing
behavior**: keep the first occurrence of each key, preserve input order, and
keep the case/whitespace-insensitive key.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `dedupe_encounters`,
  `dedupe_report` and `read_batches`, because the tests import them.
- **Don't edit:** `test_03_slow_encounter_dedup.py` and `bench.py`. The tests
  are the spec, so a pass only counts with them unchanged. To poke at the
  data, use a REPL or a scratch file.

## Run

```powershell
python -m pytest 03_python\debugging\03_slow_encounter_dedup -q
python 03_python\debugging\03_slow_encounter_dedup\bench.py
```

<details><summary>Hints</summary>

1. Doubling n roughly quadruples the time. What operation inside the loop
   gets slower as the loop goes on?
2. What is the cost of `x in some_list` versus `x in some_set`? Are the keys
   hashable?

</details>

## Say out loud

- Reproduce: the timing curve from `bench.py`, and what its shape tells you.
- Hypothesize: name the complexity (O(n^2)) and the line responsible.
- Isolate: time or profile that line (`cProfile`, or just reasoning about `in`).
- Fix: the data structure change, and why order and "first wins" still hold.
- Prevent: a performance-budget test at realistic volume; reviewing `in` on lists inside loops.
