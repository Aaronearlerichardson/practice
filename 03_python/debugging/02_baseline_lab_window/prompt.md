# 02. Baseline HbA1c is missing or stale

**Timebox: 12 min** | Fix: `03_python/debugging/02_baseline_lab_window/buggy.py`

## Input

Argument: `labs`, a `list[dict]`, for `baseline_labs(labs, index_dates)` and
`baseline_coverage(labs, index_dates, test_code)`.

```text
+------------+----------+---------------------------------------------------+
| Key        | Type     | Notes                                             |
+------------+----------+---------------------------------------------------+
| patient_id | str      | e.g. 'P1'                                         |
| test_code  | str      | e.g. 'HBA1C'                                      |
| drawn_at   | datetime | draw time from the site's LIS, in site-local time |
| value      | float    | e.g. 8.4                                          |
+------------+----------+---------------------------------------------------+
```

One dict per lab result. Every dict has all four keys.

Other arguments:

- `index_dates` (`dict[str, date]`): `patient_id` -> index date. An index
  date is a calendar date (a `date`, no time), the date of the qualifying
  encounter.
- `test_code` (`str`) for `baseline_coverage`: the test to measure, e.g.
  `'HBA1C'`.
- `lookback_days` (`int`) for `in_baseline_window` and `baseline_labs`:
  defaults to `LOOKBACK_DAYS` (30).
- `in_baseline_window(drawn_at, index_date, lookback_days)` takes one
  `drawn_at` (`datetime`) and one `index_date` (`date`).

## Ticket (from the clinical epidemiologist)

> Baseline HbA1c coverage for the diabetes test cohort came out at 50%. I
> expected 75%. Two patients I checked by hand:
>
> - **P1** had an HbA1c drawn at 10:40 on the morning of the index visit
>   (8.4%), but the baseline table shows 7.9% from three weeks earlier.
> - **P2**'s only HbA1c was drawn that afternoon, on the index date, and P2 has
>   no baseline at all.
>
> The SAP says: "most recent result within the 30 days before the index date,
> inclusive of the index date itself; day -30 is included; anything after the
> index date is excluded." Index dates are calendar dates; draw times are
> timestamps.

## Task

**Goal:** fix `buggy.py` so that the baseline window matches the SAP at both
edges: a lab counts when it was drawn at any time of day from day -30 through
day 0 (the index date), both days included.

The fixed code runs these steps. Steps 1-2 are
`in_baseline_window(drawn_at, index_date, lookback_days)`, steps 3-5 are
`baseline_labs(labs, index_dates, lookback_days)` and step 6 is
`baseline_coverage(labs, index_dates, test_code)`.

1. **Take the draw date.** The draw date is the calendar date of `drawn_at`.
   The time of day does not matter: 00:00:00 and 23:59:59 on the same day are
   treated the same.
2. **Check the window.** Return `True` when
   `index_date - lookback_days days <= draw date <= index_date`, and `False`
   otherwise. With `lookback_days = 30` and index date 2026-03-31, the window
   is 2026-03-01 00:00:00 through 2026-03-31 23:59:59.999999: 2026-03-01 is
   in, 2026-02-28 is out, 2026-04-01 00:00:00 is out.
3. **Skip patients without an index date.** Go through `labs` in list order.
   Skip a lab when its `patient_id` is not a key of `index_dates`.
4. **Keep labs in the window.** Skip a lab unless
   `in_baseline_window(drawn_at, index_dates[patient_id], lookback_days)` is
   `True`.
5. **Pick the latest per (`patient_id`, `test_code`).** For each
   (`patient_id`, `test_code`) with at least one lab left after step 4, the
   baseline is the lab with the greatest `drawn_at`. If two labs share that
   `drawn_at`, the one that comes first in `labs` wins. The value stored is
   the lab dict itself (the same object, not a copy).
6. **Compute coverage.** Run `baseline_labs(labs, index_dates)` with the
   default 30 days. Covered patients are the distinct `patient_id`s whose
   result has a key with `test_code` equal to the `test_code` argument (exact
   match, case matters). Return `covered / len(index_dates)`: patients with an
   index date but no labs count in the denominator. Return `0.0` when
   `index_dates` is empty.

## Output

| function | returns |
|---|---|
| `in_baseline_window(drawn_at, index_date, lookback_days)` | `bool`: step 2 |
| `baseline_labs(labs, index_dates, lookback_days)` | `dict[tuple[str, str], dict]`: (`patient_id`, `test_code`) -> the step 5 lab dict, with keys in the order each pair was first kept |
| `baseline_coverage(labs, index_dates, test_code)` | `float`: step 6, not rounded |

## Example

Try it on your code (inputs editable): `python tasks.py try debugging 02`.

Input (every index date is 2026-03-31, so day -30 is 2026-03-01):

```python
from datetime import date, datetime

labs = [
    {"patient_id": "P1", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 10, 9, 5), "value": 7.9},
    {"patient_id": "P1", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 31, 10, 40), "value": 8.4},
    {"patient_id": "P1", "test_code": "HBA1C", "drawn_at": datetime(2026, 4, 1, 0, 0), "value": 8.1},
    {"patient_id": "P1", "test_code": "LDL", "drawn_at": datetime(2026, 3, 31, 23, 59, 59), "value": 3.1},
    {"patient_id": "P2", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 31, 16, 20), "value": 6.2},
    {"patient_id": "P2", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 31, 16, 20), "value": 6.3},
    {"patient_id": "P3", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 1, 19, 0), "value": 9.0},
    {"patient_id": "P4", "test_code": "HBA1C", "drawn_at": datetime(2026, 2, 28, 23, 59), "value": 5.6},
    {"patient_id": "P9", "test_code": "HBA1C", "drawn_at": datetime(2026, 3, 20, 12, 0), "value": 5.1},
]
index_dates = {"P1": date(2026, 3, 31), "P2": date(2026, 3, 31),
               "P3": date(2026, 3, 31), "P4": date(2026, 3, 31)}
```

Output:

```python
>>> in_baseline_window(datetime(2026, 3, 31, 23, 59, 59), date(2026, 3, 31))
True
>>> in_baseline_window(datetime(2026, 4, 1, 0, 0), date(2026, 3, 31))
False
>>> in_baseline_window(datetime(2026, 3, 1, 0, 0), date(2026, 3, 31))
True
>>> in_baseline_window(datetime(2026, 3, 24, 8, 0), date(2026, 3, 31), lookback_days=7)
True
>>> chosen = baseline_labs(labs, index_dates)
>>> {k: v["value"] for k, v in chosen.items()}
{('P1', 'HBA1C'): 8.4,
 ('P1', 'LDL'): 3.1,
 ('P2', 'HBA1C'): 6.2,
 ('P3', 'HBA1C'): 9.0}
>>> chosen[("P1", "HBA1C")]
{'patient_id': 'P1', 'test_code': 'HBA1C', 'drawn_at': datetime.datetime(2026, 3, 31, 10, 40), 'value': 8.4}
>>> chosen[("P1", "HBA1C")] is labs[1]
True
>>> baseline_coverage(labs, index_dates, "HBA1C")
0.75
>>> baseline_coverage(labs, index_dates, "LDL")
0.25
>>> baseline_coverage(labs, {}, "HBA1C")
0.0
```

Explanation:

- **Step 1.** P1's LDL at 23:59:59 and P2's HbA1c at 16:20 both have draw
  date 2026-03-31, the index date itself.
- **Step 2.** Day 0 is in at every time of day, up to 23:59:59. 2026-04-01
  00:00 is day +1, so it is out. 2026-03-01 is day -30, so it is in. With
  `lookback_days=7` the window starts on 2026-03-24, and that day is in.
- **Step 3.** P9 has no index date, so its lab is skipped. It is not in the
  result and not in the coverage denominator.
- **Step 4.** P1's 8.1 (day +1) and P4's 5.6 (day -31, 2026-02-28) are out.
  P3's 9.0 (day -30, 19:00) is in.
- **Step 5.** P1 has two HbA1c labs in the window: 8.4 (2026-03-31 10:40)
  beats 7.9 (2026-03-10). P1's LDL is a separate key. P2 has two labs at the
  same time, 16:20, so the first in the list, 6.2, wins.
- **Step 6.** 4 patients have an index date. P1, P2 and P3 have an HbA1c
  baseline, P4 does not: 3 / 4 = 0.75. Only P1 has an LDL baseline:
  1 / 4 = 0.25. With no index dates the result is 0.0.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of
  `in_baseline_window`, `baseline_labs` and `baseline_coverage`, because the
  tests import them.
- **Don't edit:** `test_02_baseline_lab_window.py`. The tests are the spec, so
  a pass only counts with them unchanged. To poke at the data, use a REPL or a
  scratch file.

## Run the tests

```powershell
python -m pytest 03_python\debugging\02_baseline_lab_window -q
```

<details><summary>Hints</summary>

1. Write out the actual `window_start` and `window_end` values for index date
   2026-03-31. Which draw times on 2026-03-31 fall inside `[start, end]`?
2. You are comparing a calendar date with a timestamp. Either compare dates
   with dates, or use a half-open interval `[start, start_of_day_after_index)`.

</details>

## Say out loud

- Reproduce: one concrete draw time that should be in and is out.
- Hypothesize: which boundary, and what type mismatch causes it.
- Isolate: test each edge (day 0 morning and evening, day -30, day -31, day +1).
- Fix: and why you chose a closed or half-open interval.
- Prevent: boundary-value tests, and stating the inclusive/exclusive rule in the docstring.
