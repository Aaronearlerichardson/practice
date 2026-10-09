# 08. Loaded counts don't match the manifest, but rejects are always 0

**Timebox: 15 min**

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
