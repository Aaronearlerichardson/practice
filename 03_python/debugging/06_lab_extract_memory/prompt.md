# 06. Lab profiling job runs out of memory

**Timebox: 12 min**

## Ticket (from the platform team)

> The bronze profiling job for site S07 failed again with
> `MemoryError` / container OOM-killed on the Glue worker. S07's Q3 lab
> extract is 9 GB. Smaller sites are fine. We bumped the worker size once
> already and it just moved the failure to the next bigger file. The job only
> produces a tiny per-test summary (a dozen numbers per test code), so it is
> strange that it needs memory proportional to the file.

Make `summarize_lab_extract` use roughly constant memory regardless of file
size, with identical output (including TSV support via `delimiter`).

## Run

```powershell
python -m pytest 03_python\debugging\06_lab_extract_memory -q
python 03_python\debugging\06_lab_extract_memory\bench.py
```

The tests generate a ~25 MB file in a temp directory and measure peak Python
allocations with `tracemalloc`.

<details><summary>Hints</summary>

1. `bench.py` shows peak memory growing about 3x faster than the file size.
   What objects exist at the moment of the peak? (Hint: two copies of the
   file's text.)
2. A file object is already an iterator over lines, and `csv.reader` accepts
   any iterable of lines.

</details>

## Say out loud

- Reproduce: peak memory vs file size from `bench.py`.
- Hypothesize: the whole file (plus a list of every line) is materialized.
- Isolate: `tracemalloc` snapshot or reasoning about `read()` + `splitlines()`.
- Fix: stream rows; only the per-test accumulators stay in memory.
- Prevent: a memory-budget test, review rule against `.read()` / `list(reader)`
  on unbounded inputs; for pandas use `chunksize=` or `pyarrow.dataset` scans.
