# 01. QC flags that won't go away

**Timebox: 10 min**

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
