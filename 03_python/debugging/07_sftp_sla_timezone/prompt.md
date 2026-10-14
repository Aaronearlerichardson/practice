# 07. Site reported on time, audit log says late

**Timebox: 12 min** | Fix: `03_python/debugging/07_sftp_sla_timezone/buggy.py`

## Input

Argument: `arrivals`, a `list[dict]`, for `check_sla(arrivals, deadline)`.

```text
+------------+-------------+-----------------------------------------------------------+
| Key        | Type        | Notes                                                     |
+------------+-------------+-----------------------------------------------------------+
| site_id    | str         | e.g. 'S02'                                                |
| arrived_at | str or None | ISO-8601 time the site's file landed, from the SFTP event |
|            |             | log; None if the file has not arrived yet                 |
+------------+-------------+-----------------------------------------------------------+
```

One dict per site. `arrived_at` comes in three shapes:

- **With an offset** (`+HH:MM` or `-HH:MM`): the site's local clock time and
  how far that clock is from UTC. `"2026-10-15T13:05:00-04:00"` is 13:05 on
  a clock 4 hours behind UTC, which is 17:05 UTC.
- **With `Z`**: `Z` means UTC (offset `+00:00`). `"2026-10-15T16:59:00Z"` is
  16:59 UTC.
- **Naive**, from the legacy relay: `"2026-10-15T17:02:00"`. Naive means the
  string has no offset and no `Z`, so it does not say its time zone. These
  are documented to be UTC: this one is 17:02 UTC.

The `arrived_at` key can also be absent or hold `""`. Both mean the same as
`None`: not arrived yet.

Other arguments:

- `deadline` (`datetime`) for `check_sla`: the contractual deadline. It is
  timezone-aware (it carries an offset). It is usually built by
  `default_deadline` in UTC, but a caller may pass the same instant written
  with another offset, such as 13:00-04:00.
- `year` (`int`) and `quarter_due_month` (`int`, 1-12) for
  `default_deadline(year, quarter_due_month)`.
- `results` (`list[dict]`) for `late_sites(results)`: the rows that
  `check_sla` returns.

## Ticket (from the site partnerships manager)

> Our Q3 SLA report says **Harbor Health (S02)** delivered on time, so no
> escalation email went out. But the SFTP audit log shows their file landed
> at 18:30 UTC, an hour and a half after the 17:00 UTC deadline. Harbor is on
> US Eastern time.
>
> Going the other way, our European partner **S05** got an escalation email
> saying they were late, and they're upset: they uploaded at 18:45 their
> time, which they say was before the deadline.
>
> The UTC-only sites and the legacy relay (naive timestamps, documented as
> UTC) look right. Also, the `arrived_at_utc` column in the audit table for
> S02 doesn't match the SFTP server's own UTC log.

## Task

**Goal:** fix `buggy.py` so that each arrival is compared with the deadline
as an absolute instant (the same moment in time, whatever offset it is
written with), and each result row's `arrived_at_utc` is that instant
written in UTC.

The fixed code runs these steps. Step 1 is
`default_deadline(year, quarter_due_month)`. Steps 2-6 are
`check_sla(arrivals, deadline)`, run for each dict in `arrivals`, in order,
giving one row per dict. Step 7 is `late_sites(results)`.

1. **Build the deadline.** Return 17:00 UTC on the 15th of
   `quarter_due_month` in `year`. `default_deadline(2026, 10)` is
   2026-10-15 17:00+00:00. This function already works.
2. **Spot a missing file.** If `arrived_at` is absent, `None` or `""`, the
   row is `{'site_id': <site_id>, 'arrived_at_utc': None, 'status':
   'missing', 'minutes_late': None}`, and steps 3-6 are skipped for it.
3. **Read `arrived_at` as an instant.** Strip spaces from both ends and read
   the ISO-8601 string. With an offset, UTC = local time minus the offset:
   `14:30-04:00` is 18:30 UTC, and `18:45+02:00` is 16:45 UTC. With `Z`, the
   time is already UTC. Naive (no offset, no `Z`): the time is UTC.
4. **Write `arrived_at_utc`.** The step 3 instant in UTC, as
   `'YYYY-MM-DDTHH:MM:SS+00:00'`, for example `'2026-10-15T18:30:00+00:00'`.
   It always ends in `+00:00`, for `Z` and naive inputs too. The date can
   change: `'2026-10-16T01:30:00+09:00'` becomes
   `'2026-10-15T16:30:00+00:00'`.
5. **Compare with the deadline.** `late_by` = (arrival instant - deadline
   instant), in minutes, as a float (total seconds / 60). Both sides are
   instants, so a deadline passed as 13:00-04:00 gives exactly the same rows
   as one passed as 17:00+00:00. `status` is `'late'` when `late_by > 0`,
   otherwise `'on_time'`. Arriving exactly at the deadline is on time.
6. **Count the minutes late.** `minutes_late = max(0, round(late_by))`, with
   Python's `round()` to a whole number. An on-time row gets 0.
7. **List the sites to escalate.** Return the `site_id` of every row whose
   `status` is not `'on_time'` (so `'late'` or `'missing'`), sorted
   ascending.

## Output

| function | returns |
|---|---|
| `default_deadline(year, quarter_due_month)` | `datetime`, timezone-aware: step 1 |
| `check_sla(arrivals, deadline)` | `list[dict]`: one row per dict in `arrivals`, in the same order, with the keys below |
| `late_sites(results)` | `list[str]`: step 7 |

| key | type | notes |
|---|---|---|
| site_id | str | copied from the input dict |
| arrived_at_utc | str or None | step 4; `None` when `status` is `'missing'` |
| status | str | `'on_time'` or `'late'` (step 5), or `'missing'` (step 2) |
| minutes_late | int or None | step 6: 0 when `'on_time'`; `None` when `'missing'` |

## Example

Input:

```python
arrivals = [
    {"site_id": "S02", "arrived_at": "2026-10-15T14:30:00-04:00"},
    {"site_id": "S05", "arrived_at": "2026-10-15T18:45:00+02:00"},
    {"site_id": "S14", "arrived_at": "2026-10-16T01:30:00+09:00"},
    {"site_id": "S01", "arrived_at": "2026-10-15T16:59:00Z"},
    {"site_id": "S09", "arrived_at": "2026-10-15T17:02:00"},
    {"site_id": "S03", "arrived_at": "2026-10-15T13:00:00-04:00"},
    {"site_id": "S12", "arrived_at": None},
    {"site_id": "S20", "arrived_at": ""},
]
```

Output:

```python
>>> deadline = default_deadline(2026, 10)
>>> deadline
datetime.datetime(2026, 10, 15, 17, 0, tzinfo=datetime.timezone.utc)
>>> rows = check_sla(arrivals, deadline)
>>> for r in rows: print(r)
...
{'site_id': 'S02', 'arrived_at_utc': '2026-10-15T18:30:00+00:00', 'status': 'late', 'minutes_late': 90}
{'site_id': 'S05', 'arrived_at_utc': '2026-10-15T16:45:00+00:00', 'status': 'on_time', 'minutes_late': 0}
{'site_id': 'S14', 'arrived_at_utc': '2026-10-15T16:30:00+00:00', 'status': 'on_time', 'minutes_late': 0}
{'site_id': 'S01', 'arrived_at_utc': '2026-10-15T16:59:00+00:00', 'status': 'on_time', 'minutes_late': 0}
{'site_id': 'S09', 'arrived_at_utc': '2026-10-15T17:02:00+00:00', 'status': 'late', 'minutes_late': 2}
{'site_id': 'S03', 'arrived_at_utc': '2026-10-15T17:00:00+00:00', 'status': 'on_time', 'minutes_late': 0}
{'site_id': 'S12', 'arrived_at_utc': None, 'status': 'missing', 'minutes_late': None}
{'site_id': 'S20', 'arrived_at_utc': None, 'status': 'missing', 'minutes_late': None}
>>> late_sites(rows)
['S02', 'S09', 'S12', 'S20']
>>> from datetime import timedelta, timezone
>>> eastern = timezone(timedelta(hours=-4))
>>> check_sla(arrivals, deadline.astimezone(eastern)) == rows
True
```

Explanation:

- **Step 1.** The deadline is 17:00 UTC on 2026-10-15.
- **Step 2.** S12 (`None`) and S20 (`""`) have no file yet: `'missing'`,
  with `None` for `arrived_at_utc` and `minutes_late`.
- **Step 3.** S02's 14:30-04:00 is 18:30 UTC. S05's 18:45+02:00 is 16:45
  UTC. S14's 01:30+09:00 on Oct 16 is 16:30 UTC on Oct 15. S01's `Z` time is
  16:59 UTC. S09 is naive, so its 17:02 is UTC.
- **Step 4.** Every `arrived_at_utc` ends in `+00:00`, including S01
  (written with `Z`) and S09 (naive). S14's date moves back to Oct 15.
- **Step 5.** S02 arrives 90 minutes after the deadline: `'late'`. S05 and
  S14 arrive before it, so they are `'on_time'` even though their local
  clocks read later than 17:00. S03's 13:00-04:00 is exactly 17:00 UTC:
  `'on_time'`. The last call passes the deadline as 13:00-04:00 and gets the
  same rows.
- **Step 6.** S02 is 90 minutes late and S09 2. Every on-time row has 0.
- **Step 7.** S02 and S09 are late, S12 and S20 are missing; sorted, that is
  `['S02', 'S09', 'S12', 'S20']`.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `check_sla`,
  `late_sites` and `default_deadline`, because the tests import them.
- **Don't edit:** `test_07_sftp_sla_timezone.py`. The tests are the spec, so a
  pass only counts with them unchanged. To poke at the data, use a REPL or a
  scratch file.

## Run the tests

```powershell
python -m pytest 03_python\debugging\07_sftp_sla_timezone -q
```

<details><summary>Hints</summary>

1. Print `parse_arrival("2026-10-15T14:30:00-04:00")` before and after
   `.replace(tzinfo=None)`. Which clock time survives, local or UTC?
2. `replace(tzinfo=...)` relabels a time; `astimezone(...)` converts it. Make
   every value aware first (naive means UTC here), then convert to UTC.

</details>

## Say out loud

- Reproduce: S02's arrival, deadline, and the comparison result.
- Hypothesize: the offset is discarded, so local wall-clock time is compared to UTC.
- Isolate: show the naive value is 14:30, not 18:30.
- Fix: normalize to aware UTC at the boundary (parse), compare aware to aware.
- Prevent: "aware UTC everywhere inside the pipeline" rule; reject or
  explicitly default naive input at parse time; tests with non-UTC offsets.
