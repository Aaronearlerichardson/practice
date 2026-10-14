# 08. Loaded counts don't match the manifest, but rejects are always 0

**Timebox: 15 min** | Fix: `03_python/debugging/08_silent_batch_rejects/buggy.py`

## Input

File: a site's quarterly encounter batch, passed as `path` to
`load_batch(path)`. CSV, UTF-8, with a header row.

```text
+--------------+------+------------------------------------------------------------+
| Column Name  | Type | Notes                                                      |
+--------------+------+------------------------------------------------------------+
| encounter_id | text | e.g. 'E001'                                                |
| patient_id   | text | e.g. 'P001'; required                                      |
| admit_ts     | text | 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS', site-local    |
|              |      | time; required                                             |
| discharge_ts | text | same two formats as admit_ts; may be blank                 |
| weight_kg    | text | weight in kg, e.g. '72.5'; may be blank                    |
+--------------+------+------------------------------------------------------------+
```

One row per encounter. Line 1 is the header, always exactly these five
column names in this order. Each data row is one line of the file (no blank
lines, no line breaks inside a field). The site's old EHR export writes
times without seconds (`'2026-07-01 08:15'`), and its new export adds
seconds (`'2026-07-03 07:12:45'`). Both are valid. Each delivery comes with
a manifest stating the number of data rows (not counting the header).

Other arguments:

- `raw` (`dict`) for `parse_row(raw)`: one data row as `csv.DictReader`
  reads it, header column name -> that field's text.
- `result` (`LoadResult`) for `reconcile(result, manifest_rows)`: what
  `load_batch` returns (fields `rows`, `rejects` and `n_input`).
- `manifest_rows` (`int`): the number of data rows the site's manifest
  states.

## Ticket (from the data operations analyst)

> Site S04's Q3 encounter batch: the manifest says 11 data rows. The load log
> says `loaded=4, rejected=0, ok=False`. Every batch from every site shows
> `rejected=0`, which can't be right, and when `ok` is False I have no way to
> tell the site which rows to fix.
>
> Also, S04 switched to a new EHR export this quarter and their
> encounter counts dropped more than I'd expect from a few bad rows. Their
> rows look fine to me when I open the file.
>
> What I need: every input row either loaded or listed as a reject with a
> line number and a reason I can send back to the site, and a reconciliation
> that only says ok when loaded + rejected accounts for the manifest.

## Task

**Goal:** fix `buggy.py` so that every data row ends up either loaded into
`rows` or listed in `rejects` with its line number and a reason. Bad data
becomes a reject; a bug in our own code still crashes the job loudly. And
`reconcile` says `ok` only when loaded + rejected accounts for every row in
the manifest.

The fixed code runs these steps. Steps 1, 2 and 7 are `load_batch(path)`.
Steps 3-6 are `parse_row(raw)`, which `load_batch` calls once for each row
that passes step 2: it returns the typed record, or raises `ValueError`
whose message is the reject reason. Step 8 is
`reconcile(result, manifest_rows)`.

1. **Read the rows.** Read the file with its header. Number each data row by
   its line in the file: the header is line 1, so the k-th data row
   (counting from 1) has `line_no` k + 1. `n_input` is the number of data
   rows. Steps 2-7 run for each row, in file order.
2. **Check the column count.** A row must have exactly 5 fields, one per
   header column. A row with N fields, N not 5, is rejected with reason
   `'columns: expected 5, got N'` (for example
   `'columns: expected 5, got 3'`), and steps 3-6 are skipped for it.
3. **Check `patient_id`.** Strip spaces from both ends. If the result is
   `""`, the reason is `'patient_id: missing'`.
4. **Parse `admit_ts`.** Strip spaces from both ends, then read it as
   `YYYY-MM-DD HH:MM` or `YYYY-MM-DD HH:MM:SS` into a `datetime` with no time
   zone attached (it stays site-local). Anything else, blank included, gives
   the reason `'admit_ts: bad format'`.
5. **Parse `discharge_ts`.** Strip spaces from both ends. Blank means
   `None`. Otherwise read it with the same two formats, or the reason is
   `'discharge_ts: bad format'`. If it is earlier than `admit_ts`, the reason
   is `'discharge_ts: before admit_ts'`. Equal to `admit_ts` is fine.
6. **Parse `weight_kg`.** Blank (after stripping) means `None`. Otherwise it
   must be a number that Python's `float()` accepts, such as `'72.5'` or
   `'80'`, or the reason is `'weight_kg: not a number'`. There is no range
   check.
7. **Load or reject.** A row that passes steps 2-6 is appended to `rows` as
   a dict with `encounter_id` and `patient_id` (both stripped), `admit_ts`,
   `discharge_ts` and `weight_kg`. A row that fails is appended to `rejects`
   as `{'line_no', 'reason', 'raw'}`, with the reason of the first check
   that failed, in step order, so each bad row gives exactly one reject.
   Only a `ValueError` from `parse_row` becomes a reject. Any other
   exception, such as a `TypeError` from a bug in `parse_row`, propagates
   out of `load_batch`, and the load stops.
8. **Reconcile.** `loaded = len(result.rows)` and
   `rejected = len(result.rejects)`. `ok` is `True` only when
   `loaded + rejected == result.n_input` and
   `result.n_input == manifest_rows`.

The tests check that each reason contains its column name (`'column'` for
step 2). The exact strings above are the spec, and the Example uses them.

## Output

| function | returns |
|---|---|
| `parse_row(raw)` | `dict`: one loaded row (keys below), or raises `ValueError(<reason>)` |
| `load_batch(path)` | `LoadResult` with the three fields below |
| `reconcile(result, manifest_rows)` | `dict` with the four keys below |

`LoadResult`:

| field | type | notes |
|---|---|---|
| rows | list[dict] | step 7: loaded rows, in file order |
| rejects | list[dict] | step 7: one per rejected row, in file order |
| n_input | int | step 1: number of data rows in the file |

A loaded row (an item of `rows`):

| key | type | notes |
|---|---|---|
| encounter_id | str | `encounter_id`, stripped; not checked |
| patient_id | str | step 3: `patient_id`, stripped |
| admit_ts | datetime | step 4, no time zone |
| discharge_ts | datetime or None | step 5; `None` when blank |
| weight_kg | float or None | step 6; `None` when blank |

A reject (an item of `rejects`):

| key | type | notes |
|---|---|---|
| line_no | int | step 1 |
| reason | str | the step 2-6 reason, exactly as written above |
| raw | dict | the row as `csv.DictReader` reads it: header column name -> text. A short row's missing columns are `None`; a long row's extra fields are a list under the key `None` |

`reconcile(result, manifest_rows)`:

| key | type | notes |
|---|---|---|
| manifest_rows | int | the `manifest_rows` argument |
| loaded | int | step 8: `len(result.rows)` |
| rejected | int | step 8: `len(result.rejects)` |
| ok | bool | step 8 |

## Example

Input file `S04_encounters_2026Q3.csv`. The `line |` column shows line
numbers and is not part of the file:

```text
line | file text
   1 | encounter_id,patient_id,admit_ts,discharge_ts,weight_kg
   2 | E101,P101,2026-07-01 08:15,2026-07-03 11:00,72.5
   3 | E102,P102,2026-07-03 07:12:45,2026-07-04 10:00:00,64.0
   4 | E103,P103,2026-07-03 09:40,,
   5 | E104,P104,2026-07-04 10:00,2026-07-04 10:00,80
   6 | E105, ,2026-07-04 10:00,2026-07-05 10:00,heavy
   7 | E106,P106,07/04/2026 10:00,,70.0
   8 | E107,P107,2026-07-05 10:00,2026-07-06,70.0
   9 | E108,P108,2026-07-05 10:00,2026-07-04 09:00,70.0
  10 | E109,P109,2026-07-05 12:00,,seventy
  11 | E110,P110,2026-07-06 08:00
  12 | E111,P111,2026-07-06 09:30,,55.2,kg
```

Output:

```python
>>> result = load_batch("S04_encounters_2026Q3.csv")
>>> result.n_input
11
>>> [r["encounter_id"] for r in result.rows]
['E101', 'E102', 'E103', 'E104']
>>> result.rows[1]
{'encounter_id': 'E102', 'patient_id': 'P102',
 'admit_ts': datetime.datetime(2026, 7, 3, 7, 12, 45),
 'discharge_ts': datetime.datetime(2026, 7, 4, 10, 0), 'weight_kg': 64.0}
>>> result.rows[2]
{'encounter_id': 'E103', 'patient_id': 'P103',
 'admit_ts': datetime.datetime(2026, 7, 3, 9, 40), 'discharge_ts': None, 'weight_kg': None}
>>> result.rows[3]["discharge_ts"] == result.rows[3]["admit_ts"]
True
>>> [(r["line_no"], r["reason"]) for r in result.rejects]
[(6, 'patient_id: missing'), (7, 'admit_ts: bad format'), (8, 'discharge_ts: bad format'),
 (9, 'discharge_ts: before admit_ts'), (10, 'weight_kg: not a number'),
 (11, 'columns: expected 5, got 3'), (12, 'columns: expected 5, got 6')]
>>> result.rejects[5]["raw"]
{'encounter_id': 'E110', 'patient_id': 'P110', 'admit_ts': '2026-07-06 08:00',
 'discharge_ts': None, 'weight_kg': None}
>>> result.rejects[6]["raw"]
{'encounter_id': 'E111', 'patient_id': 'P111', 'admit_ts': '2026-07-06 09:30',
 'discharge_ts': '', 'weight_kg': '55.2', None: ['kg']}
>>> reconcile(result, 11)
{'manifest_rows': 11, 'loaded': 4, 'rejected': 7, 'ok': True}
>>> reconcile(result, 12)
{'manifest_rows': 12, 'loaded': 4, 'rejected': 7, 'ok': False}
>>> import buggy
>>> def broken(raw):
...     raise TypeError("bug in parser, not bad data")
...
>>> buggy.parse_row = broken
>>> buggy.load_batch("S04_encounters_2026Q3.csv")
Traceback (most recent call last):
  ...
TypeError: bug in parser, not bad data
```

Explanation:

- **Step 1.** The file has 11 data rows on lines 2-12, so `n_input` is 11.
  E105 is the 5th data row, so its `line_no` is 6.
- **Step 2.** Line 11 has 3 fields and line 12 has 6, so both are rejected
  on their column count. Line 12's extra field `'kg'` sits under the key
  `None` in its `raw`.
- **Step 3.** Line 6's `patient_id` is a single space, which strips to
  `""`: `'patient_id: missing'`. Its weight `'heavy'` is also bad, but the
  first failing check gives the only reason.
- **Step 4.** Line 2 (no seconds) and line 3 (with seconds) both parse.
  Line 7's `'07/04/2026 10:00'` is neither format.
- **Step 5.** Line 4's blank discharge becomes `None`. Line 8's
  `'2026-07-06'` has no time, so it is a bad format. Line 9 is discharged
  the day before admission. Line 5's discharge equals its admission, which
  is fine.
- **Step 6.** Line 4's blank weight becomes `None`, line 5's `'80'` becomes
  `80.0`, and line 10's `'seventy'` is not a number.
- **Step 7.** 4 rows are loaded and 7 are rejected, each in file order.
  When `parse_row` itself is broken and raises `TypeError`, `load_batch`
  does not turn it into rejects: the error comes straight out.
- **Step 8.** 4 + 7 = 11 = `n_input`, and the manifest says 11: `ok` is
  `True`. With a manifest of 12, one row is unaccounted for: `ok` is
  `False`.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `load_batch`,
  `reconcile` and `parse_row`, because the tests import or replace them.
  `load_batch` must call `parse_row` for each row it parses, because one
  test swaps in a broken `parse_row`. `LoadResult` keeps its `rows`,
  `rejects` and `n_input` fields.
- **Don't edit:** `test_08_silent_batch_rejects.py`. The tests are the spec,
  so a pass only counts with them unchanged. To poke at the data, use a REPL
  or a scratch file.

## Run the tests

```powershell
python -m pytest 03_python\debugging\08_silent_batch_rejects -q
```

<details><summary>Hints</summary>

1. Temporarily change `except Exception: continue` to
   `except Exception as e: print(line_no, repr(e))` (or re-raise) and run
   the loader. How many distinct failure causes are there, and are all of
   them really bad data?
2. Catch only the exceptions bad data can cause (`ValueError`), turn each into
   a reject with a field-specific reason, validate row shape explicitly
   (`csv.DictReader` fills missing fields with `None`), and accept the
   timestamp formats the contract actually allows.

</details>

## Say out loud

- Reproduce: manifest vs loaded vs rejected for the sample batch.
- Hypothesize: a broad `except` is hiding failures, and maybe some are ours.
- Isolate: surface every exception with its line number; classify data vs code errors.
- Fix: narrow the except, record rejects with reasons, fix the timestamp parser,
  reconcile loaded + rejected == input == manifest.
- Prevent: lint against `except Exception: pass/continue` (ruff BLE001, S112),
  a reconciliation check that fails the Step Functions task, and tests with
  each kind of bad row.
