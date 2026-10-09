# 03. Encounter dedup step is timing out

**Timebox: 10 min**

## Ticket (from the on-call data engineer)

> The `dedupe_encounters` Glue job used to finish in seconds. Since the large
> academic site (S07) joined, it has been running for hours, and last night it
> hit the 2-hour task timeout in Step Functions. The output is correct when it
> does finish. Volume went from ~20k encounters per quarter to ~1M.
>
> Local repro: `bench.py` shows 10k rows taking under a second, 20k taking
> about 4x longer, 40k about 4x longer again.

Make it fast enough for 1M rows in a few seconds **without changing
behavior**: keep the first occurrence of each key, preserve input order, and
keep the case/whitespace-insensitive key.

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
