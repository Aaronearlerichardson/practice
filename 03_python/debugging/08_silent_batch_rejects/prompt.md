# 08. Loaded counts don't match the manifest, but rejects are always 0

**Timebox: 15 min**

## Input

File: a site's quarterly encounter batch, passed as `path` to
`load_batch(path)`. CSV, UTF-8, with a header row.

```text
+--------------+------+--------------------------------------------------------+
| Column Name  | Type | Notes                                                  |
+--------------+------+--------------------------------------------------------+
| encounter_id | text | e.g. 'E001'                                            |
| patient_id   | text | e.g. 'P001'                                            |
| admit_ts     | text | "YYYY-MM-DD HH:MM[:SS]", site-local time               |
| discharge_ts | text | "YYYY-MM-DD HH:MM[:SS]", site-local time; may be blank |
| weight_kg    | text | weight in kg, e.g. '72.5'; may be blank                |
+--------------+------+--------------------------------------------------------+
```

One row per encounter. Each delivery comes with a manifest stating the
number of data rows.

Other arguments:

- `result` for `reconcile(result, manifest_rows)`: the `LoadResult` that
  `load_batch` returns (`rows`, `rejects` as `{line_no, reason, raw}`, and
  `n_input`).
- `manifest_rows` (`int`): the number of data rows the site's manifest states.

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

Fix `buggy.py`. Bugs in our own code should still crash the job loudly;
only bad *data* should become rejects.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `load_batch` and
  `reconcile`, because the tests import them. `LoadResult` keeps its `rows`,
  `rejects` and `n_input` fields.
- **Don't edit:** `test_08_silent_batch_rejects.py`. The tests are the spec,
  so a pass only counts with them unchanged. To poke at the data, use a REPL
  or a scratch file.

## Run the tests

```powershell
python -m pytest 03_python\debugging\08_silent_batch_rejects -q
```

<details><summary>Hints</summary>

1. Temporarily replace `continue` in the `except` with `print(line_no, repr(e))`
   (or re-raise) and run the loader. How many distinct failure causes are
   there, and are all of them really bad data?
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
