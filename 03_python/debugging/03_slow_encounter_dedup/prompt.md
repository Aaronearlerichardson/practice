# 03. Encounter dedup step is timing out

**Timebox: 10 min** | Fix: `03_python/debugging/03_slow_encounter_dedup/buggy.py`

## Input

Argument: `rows`, a `list[dict]`, for `dedupe_encounters(rows, key_fields)`
and `dedupe_report(rows)`.

```text
+--------------+------+--------------------------------------------------+
| Key          | Type | Notes                                            |
+--------------+------+--------------------------------------------------+
| site_id      | str  | key field, e.g. 'S01'                            |
| patient_id   | str  | key field, e.g. 'P0000001'                       |
| encounter_id | str  | key field, e.g. 'E00000001'                      |
| source_file  | str  | delivery file name, e.g. 'q3.csv'; read_batches  |
|              |      | adds it                                          |
+--------------+------+--------------------------------------------------+
```

One dict per encounter row, in delivery order (earliest delivery first). The
same encounter can arrive more than once, with different letter case or
extra spaces around a key value. A row can hold other keys too; they are
passed through unchanged. A large site sends about 1,000,000 rows per
quarter.

Other arguments:

- `key_fields` (`tuple[str, ...]`) for `dedupe_encounters`: the keys that
  identify an encounter. Defaults to `KEY_FIELDS`,
  `("site_id", "patient_id", "encounter_id")`.
- `paths` (`list[Path]`) for `read_batches(paths)`: CSV file paths in
  delivery order. Each file is UTF-8 with a header row that includes the key
  fields.

## Ticket (from the on-call data engineer)

> The `dedupe_encounters` Glue job used to finish in seconds. Since the large
> academic site (S07) joined, it has been running for hours, and last night it
> hit the 2-hour task timeout in Step Functions. The output is correct when it
> does finish. Volume went from ~20k encounters per quarter to ~1M.
>
> Local repro: `bench.py` shows 10k rows taking about a second, 20k taking
> about 4x longer, 40k about 4x longer again.

## Task

**Goal:** make `dedupe_encounters` fast enough for a 1,000,000-row quarter,
while every function returns exactly what it returns today: one row per
encounter key, the first one delivered, in input order.

The behavior below must not change. Step 1 is `read_batches(paths)`, steps
2-3 are `dedupe_encounters(rows, key_fields)` and step 4 is
`dedupe_report(rows)`.

1. **Read the batches.** For each path in `paths`, in list order, read the
   CSV file (UTF-8, first line is the header). Each data line becomes a dict
   of header name -> value, all values `str`, exactly as written (spaces
   kept). Add `source_file` = the file name without its folder, for example
   `'q3.csv'`. Return all rows in one list: the first file's rows in file
   order, then the second file's, and so on.
2. **Build each row's key.** For each field in `key_fields`, in order, take
   `str(row[field])`, remove leading and trailing whitespace, and upper-case
   it. The key is the tuple of these strings. So `'s01 '` and `'S01'` match,
   and `' e2'` and `'E2'` match, but spaces inside a value still count. A row
   without one of the key fields raises `KeyError`.
3. **Keep the first row per key.** Go through `rows` in list order. Keep a
   row when no earlier row has the same key, and drop it otherwise. Return
   the kept rows in their input order. They are the original dict objects,
   not copies, and none of their values change (the original spelling stays,
   for example `'s01 '`).
4. **Count.** Run `dedupe_encounters(rows)` with the default `KEY_FIELDS`.
   Return `n_input` = `len(rows)`, `n_kept` = number of rows step 3 kept, and
   `n_duplicates_dropped` = `n_input - n_kept`.

**Speed target (tested).** `test_perf_budget` builds 40,000 rows with the test
file's `make_rows(40_000)` (about 10% of rows repeat an earlier key) and
times one `dedupe_encounters(rows)` call in a separate process. It must take
under 1.0 s; the process is stopped after 6 s. `bench.py` times the
production size, 1,000,000 rows in under 5 s. The tests do not run it, but
it is the real goal.

## Output

| function | returns |
|---|---|
| `read_batches(paths)` | `list[dict]`: step 1, every row of every file, each with `source_file` added |
| `dedupe_encounters(rows, key_fields)` | `list[dict]`: step 3, the first row for each step 2 key, in input order |
| `dedupe_report(rows)` | `dict` with the three keys below |

| key | type | notes |
|---|---|---|
| n_input | int | `len(rows)` |
| n_kept | int | `len(dedupe_encounters(rows))` |
| n_duplicates_dropped | int | `n_input - n_kept` |

## Example

Try it on your code (inputs editable): `python tasks.py try debugging 03`.

Input: two delivery files, in this order.

`q2.csv`:

```text
site_id,patient_id,encounter_id
S01,P1,E1
S01,P2,E2
S01,P2,E2
```

`q3.csv` (the second data line has a space after `s01` and before `e2`):

```text
site_id,patient_id,encounter_id
S01,P2,E2
s01 ,p2, e2
S02,P1,E1
S01,P3,E3
```

Output:

```python
>>> rows = read_batches([Path("q2.csv"), Path("q3.csv")])
>>> rows
[{'site_id': 'S01', 'patient_id': 'P1', 'encounter_id': 'E1', 'source_file': 'q2.csv'},
 {'site_id': 'S01', 'patient_id': 'P2', 'encounter_id': 'E2', 'source_file': 'q2.csv'},
 {'site_id': 'S01', 'patient_id': 'P2', 'encounter_id': 'E2', 'source_file': 'q2.csv'},
 {'site_id': 'S01', 'patient_id': 'P2', 'encounter_id': 'E2', 'source_file': 'q3.csv'},
 {'site_id': 's01 ', 'patient_id': 'p2', 'encounter_id': ' e2', 'source_file': 'q3.csv'},
 {'site_id': 'S02', 'patient_id': 'P1', 'encounter_id': 'E1', 'source_file': 'q3.csv'},
 {'site_id': 'S01', 'patient_id': 'P3', 'encounter_id': 'E3', 'source_file': 'q3.csv'}]
>>> kept = dedupe_encounters(rows)
>>> kept
[{'site_id': 'S01', 'patient_id': 'P1', 'encounter_id': 'E1', 'source_file': 'q2.csv'},
 {'site_id': 'S01', 'patient_id': 'P2', 'encounter_id': 'E2', 'source_file': 'q2.csv'},
 {'site_id': 'S02', 'patient_id': 'P1', 'encounter_id': 'E1', 'source_file': 'q3.csv'},
 {'site_id': 'S01', 'patient_id': 'P3', 'encounter_id': 'E3', 'source_file': 'q3.csv'}]
>>> kept[3] is rows[6]
True
>>> dedupe_report(rows)
{'n_input': 7, 'n_kept': 4, 'n_duplicates_dropped': 3}
>>> dedupe_encounters(rows, ("patient_id",))
[{'site_id': 'S01', 'patient_id': 'P1', 'encounter_id': 'E1', 'source_file': 'q2.csv'},
 {'site_id': 'S01', 'patient_id': 'P2', 'encounter_id': 'E2', 'source_file': 'q2.csv'},
 {'site_id': 'S01', 'patient_id': 'P3', 'encounter_id': 'E3', 'source_file': 'q3.csv'}]
```

Explanation:

- **Step 1.** 3 rows from `q2.csv`, then 4 from `q3.csv`, each tagged with
  its file name. The spaces in `'s01 '` and `' e2'` are kept.
- **Step 2.** Rows 1, 2, 3 and 4 (counting from 0) all have key
  `('S01', 'P2', 'E2')`: `'s01 '` -> `'S01'`, `'p2'` -> `'P2'`,
  `' e2'` -> `'E2'`. `('S02', 'P1', 'E1')` differs from `('S01', 'P1', 'E1')`
  because `site_id` is part of the key.
- **Step 3.** For `('S01', 'P2', 'E2')` the `q2.csv` row comes first, so the
  earliest delivery wins and the other three are dropped. The kept rows are
  the same objects as in `rows`. With `key_fields=("patient_id",)` the key is
  only the patient, so `S02`'s P1 row is dropped as a repeat of `S01`'s.
- **Step 4.** 7 rows in, 4 kept, 7 - 4 = 3 dropped.

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
