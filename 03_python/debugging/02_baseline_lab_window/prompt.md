# 02. Baseline HbA1c is missing or stale

**Timebox: 12 min**

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

Fix `buggy.py` so the window matches the SAP at **both** edges.

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
