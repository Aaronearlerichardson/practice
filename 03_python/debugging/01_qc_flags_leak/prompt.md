# 01. QC flags that won't go away

**Timebox: 10 min**

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
| age            | int   | optional; years, plausible 0 to 120 inclusive |
| sex            | str   | optional; 'F', 'M' or 'U'                     |
| weight_kg      | float | optional; plausible 0.3 to 350.0 inclusive    |
+----------------+-------+-----------------------------------------------+
```

One dict per encounter record in a site's quarterly batch. A required field
counts as missing if it is absent, `None` or `""`. An optional field is only
checked when it is present.

Other arguments:

- `flags` (`list[str]`, optional): seed flags raised upstream, such as by the
  file-level parser, so everything is reported together.
- `results` for `summarize(results)`: what `validate_batch` returns, a
  `dict[str, list[str]]` from record_id to that record's flags.

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

`collect_flags` and `validate_batch` live in `buggy.py`. Find out why flags
leak between records and runs, fix it, and keep the public signatures the same
(callers still pass seed flags as the second argument).

## Run the tests

```powershell
python -m pytest 03_python\debugging\01_qc_flags_leak -q
```

<details><summary>Hints</summary>

1. Call `collect_flags` on a clean record twice in a row in a REPL. Does the
   second call return what the first did? Then check `is` between two results.
2. When is a function's default argument value evaluated: at each call, or once?

</details>

## Say out loud

- Reproduce: the smallest call sequence that shows the leak.
- Hypothesize: what state survives between calls?
- Isolate: prove it with `id()` / `is` on the returned lists.
- Fix: and why it is the idiomatic fix.
- Prevent: what lint rule or test would have caught it?
