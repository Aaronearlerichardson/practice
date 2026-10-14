# 01. QC flags that won't go away

**Timebox: 10 min** | Fix: `03_python/debugging/01_qc_flags_leak/buggy.py`

## Input

Argument: `records`, a `list[dict]`, for `validate_batch(records)`.
`collect_flags(record, flags)` takes one of these dicts as `record`.

```text
+----------------+-------+-----------------------------------------------+
| Key            | Type  | Notes                                         |
+----------------+-------+-----------------------------------------------+
| record_id      | str   | required                                      |
| patient_id     | str   | required, e.g. 'P001'                         |
| site_id        | str   | required, e.g. 'S01'                          |
| encounter_date | str   | required, 'YYYY-MM-DD'                        |
| age            | int   | optional; years                               |
| sex            | str   | optional                                      |
| weight_kg      | float | optional                                      |
+----------------+-------+-----------------------------------------------+
```

One dict per encounter record in a site's quarterly batch. Any key can be
absent, and any value can be `None`.

Other arguments:

- `flags` (`list[str]`, optional) for `collect_flags`: seed flags raised
  upstream, such as `'parse:trailing_delimiter'` from the file-level parser,
  so everything is reported together. Callers pass it as the second
  positional argument or leave it out.
- `results` (`dict[str, list[str]]`) for `summarize(results)`: what
  `validate_batch` returns.

## Ticket (from the data quality analyst)

> The site QC dashboard looks wrong since we started running validation in the
> long-lived Step Functions worker. For site S01's July batch it says 0% of
> records are clean, but I opened the file and most rows are fine: R1, R3 and
> R5 have every required field and plausible values.
>
> Weirder: if I re-run validation on the *same* batch, the flag counts go up.
> The first record of a batch sometimes looks fine when I test it on its own in
> a fresh notebook, but in the worker every record shows flags like
> `missing:patient_id` even when the patient ID is there.

## Task

**Goal:** fix `buggy.py` so that each record's flag list holds only that
record's own problems (after any seed flags passed with it), and running the
same batch twice gives the same answer.

The fixed code runs these steps. Steps 1-5 are `collect_flags(record, flags)`,
step 6 is `validate_batch(records)` and step 7 is `summarize(results)`.

1. **Start a new list.** Start from a new list holding the seed `flags` in the
   order given, or an empty list when no `flags` argument is passed. Nothing
   from an earlier call carries over, and the caller's seed list is not
   changed.
2. **Check the required keys.** For each of `record_id`, `patient_id`,
   `site_id`, `encounter_date`, in that order, append `'missing:<key>'` (for
   example `'missing:patient_id'`) when the key is absent, its value is `None`
   or its value is `""`.
3. **Check `age`.** When `age` is present and not `None`, append
   `'implausible:age'` unless `0 <= age <= 120`.
4. **Check `weight_kg`.** When `weight_kg` is present and not `None`, append
   `'implausible:weight_kg'` unless `0.3 <= weight_kg <= 350.0`.
5. **Check `sex`.** When `sex` is present and not `None`, append
   `'invalid:sex'` unless it is exactly `'F'`, `'M'` or `'U'` (case matters).
   Return the list.
6. **Validate the batch.** For the record at 0-based position `i` in
   `records`, the key is its `record_id`, or `'<row i>'` (for example
   `'<row 5>'`) when `record_id` is absent, `None` or `""`. The value is
   `collect_flags(record)`, with no seed. If two records share a `record_id`,
   the later one's list replaces the earlier one's.
7. **Summarize.** Count the step 6 results: see the `summarize` keys below.

## Output

| function | returns |
|---|---|
| `collect_flags(record, flags)` | `list[str]`: the seed flags, then the step 2-5 flags in step order |
| `validate_batch(records)` | `dict[str, list[str]]`: step 6 key -> that record's `collect_flags` list |
| `summarize(results)` | `dict` with the four keys below |

| key | type | notes |
|---|---|---|
| n_records | int | `len(results)` |
| n_clean | int | number of records whose flag list is empty |
| clean_rate | float or None | `round(n_clean / n_records, 3)`; `None` when `results` is empty |
| flag_counts | dict[str, int] | each flag string -> how many times it appears across all the lists |

## Example

Input:

```python
records = [
    {"record_id": "R1", "patient_id": "P001", "site_id": "S01", "encounter_date": "2026-07-02",
     "age": 54, "sex": "F", "weight_kg": 71.2},
    {"record_id": "R2", "patient_id": "", "site_id": "S01", "encounter_date": "2026-07-03",
     "age": 61, "sex": "M", "weight_kg": 88.0},
    {"record_id": "R3", "patient_id": "P003", "site_id": "S01", "encounter_date": "2026-07-03"},
    {"record_id": "R4", "patient_id": "P004", "site_id": "S01", "encounter_date": "2026-07-05",
     "age": 212, "sex": "X", "weight_kg": 80.1},
    {"record_id": "R5", "patient_id": "P005", "site_id": None, "encounter_date": "2026-07-06",
     "age": 120, "sex": "U", "weight_kg": 0.1},
    {"patient_id": "P006", "site_id": "S01", "encounter_date": "2026-07-07",
     "age": 0, "sex": "f"},
]
```

Output:

```python
>>> validate_batch(records)
{'R1': [],
 'R2': ['missing:patient_id'],
 'R3': [],
 'R4': ['implausible:age', 'invalid:sex'],
 'R5': ['missing:site_id', 'implausible:weight_kg'],
 '<row 5>': ['missing:record_id', 'invalid:sex']}
>>> validate_batch(records) == validate_batch(records)
True
>>> summarize(validate_batch(records))
{'n_records': 6, 'n_clean': 2, 'clean_rate': 0.333,
 'flag_counts': {'missing:patient_id': 1, 'implausible:age': 1, 'invalid:sex': 2,
                 'missing:site_id': 1, 'implausible:weight_kg': 1, 'missing:record_id': 1}}
>>> seed = ["parse:trailing_delimiter"]
>>> collect_flags(records[1], seed)
['parse:trailing_delimiter', 'missing:patient_id']
>>> seed
['parse:trailing_delimiter']
```

Explanation:

- **Step 1.** R3 comes after records with problems, and its list is still
  empty: nothing carries over between calls, so a second run of the batch
  gives the same dict. In the last call the list starts with the seed flag,
  and `seed` itself still holds one item afterwards.
- **Step 2.** R2's `patient_id` is `""` and R5's `site_id` is `None`: both
  count as missing. The last record has no `record_id` key at all.
- **Step 3.** R4's age 212 is out of range. R5's 120 and the last record's 0
  are in range, because both ends count. R3 has no `age`, so it is not
  checked.
- **Step 4.** R5's 0.1 kg is below 0.3.
- **Step 5.** R4's `'X'` is invalid, and so is the last record's `'f'`:
  `'f'` is not `'F'`.
- **Step 6.** The last record has no `record_id`, so its key is `'<row 5>'`
  (position 5, counting from 0).
- **Step 7.** 6 records, 2 with an empty list (R1, R3): `clean_rate` =
  round(2 / 6, 3) = 0.333. `invalid:sex` appears twice (R4 and `<row 5>`).

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `collect_flags`,
  `validate_batch` and `summarize`, because the tests import them. Both
  `collect_flags(record)` and `collect_flags(record, seed_flags)` must still
  work.
- **Don't edit:** `test_01_qc_flags_leak.py`. The tests are the spec, so a
  pass only counts with them unchanged. To poke at the data, use a REPL or a
  scratch file.

## Run the tests

```powershell
python -m pytest 03_python\debugging\01_qc_flags_leak -q
```

<details><summary>Hints</summary>

1. Call `collect_flags` on a clean record twice in a row in a REPL. Does the
   second call return what the first did? Then check `is` between two results.
2. When is a function's default argument value evaluated: at each call, or once?
3. After your fix, pass a seed list, then print the seed list. Is it still the
   list you passed in?

</details>

## Say out loud

- Reproduce: the smallest call sequence that shows the leak.
- Hypothesize: what state survives between calls?
- Isolate: prove it with `id()` / `is` on the returned lists.
- Fix: and why it is the idiomatic fix.
- Prevent: what lint rule or test would have caught it?
