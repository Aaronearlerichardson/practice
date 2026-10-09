# 03. Two gigabytes, ten megabytes

**Timebox: 35 min**

A site's quarterly lab extract is 2 GB, and the container that profiles it has far less memory than that to spare. In **one pass** and **constant memory**, compute per-(site, test) stats for the quality dashboard, and stream every invalid row to a rejects file as you go.

## Inputs

- `data/labs_sample.csv`: 300 rows (the first 16 are handcrafted traps). Use it while you develop.
- `python gen_data.py --size-mb 2000` writes `data/big/labs_big.csv` (gitignored). `python tasks.py gen-data --big-mb 2000` does the same from the repo root. Start with 200.

Columns: `row_id, site_id, patient_id, test_code, collected_date, value, unit`. You may assume every line has 7 fields. Quoting is standard CSV.

## Outputs

**Summary CSV**: `site_id, test_code, count, invalid_count, mean, min, max`, one row per group, sorted by `site_id, test_code`.

**Rejects CSV**: the 7 input columns exactly as read (raw text) plus `reason`, in input order.

## Rules

| # | Rule |
|---|---|
| 1 | Group key is `(site_id.strip(), test_code.strip().upper())`. Every row, valid or not, belongs to its group. |
| 2 | A row is invalid if (checked in order) its test code is not in `PLAUSIBLE`: `unknown_test`; or its value (trimmed) is not a **finite** float: `non_numeric`; or the value is outside the inclusive `PLAUSIBLE` range: `implausible`. |
| 3 | Valid rows feed `count`, `mean`, `min`, `max`. Invalid rows add to `invalid_count` and go to rejects. |
| 4 | `mean` is written with exactly 4 decimals (`f"{m:.4f}"`). `min`/`max` can be written in any form that parses back to the same float. |
| 5 | A group with no valid rows still appears: `count` 0, and `mean`, `min`, `max` empty. |
| 6 | Memory must not grow with the file: the test traces peak Python allocations on a ~30 MB file and requires **< 8 MB**. |

`PLAUSIBLE`: GLU 10-1000, HBA1C 2-20, K 1.5-10, NA 100-180, HGB 2-25, CREAT 0.1-20 (also in `solution.py`).

## Implement (in `solution.py`)

```python
def classify(test_code: str, value: str) -> tuple[float | None, str | None]
def summarize(in_path, summary_path, rejects_path) -> dict[str, int]   # rows_read, valid, invalid
```

## Run the tests (PowerShell, from the repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest 03_python\data_tasks\03_streaming_aggregates -q -p no:cacheprovider
```

The memory test generates a 30 MB file in a temp dir, so the run takes 10-30 s.

<details><summary>Hints</summary>

- `csv.reader` over an open file is already a stream. Keep a dict of `group -> [count, sum, min, max, invalid]` and write each reject the moment you see it.
- Memory is O(groups), not O(rows). 12 sites x 7 codes is 84 entries.
- `float("1e2")` is 100 and is valid. `float("nan")` and `float("inf")` succeed, so check `math.isfinite`.
- pandas works if you use `chunksize` with `dtype=str, keep_default_na=False`, and keep chunks around 20-50k rows. 
- Don't collect the rejects in a list and write them at the end. 

</details>

<details><summary>Check yourself</summary>

On `data/labs_sample.csv`:

- `{"rows_read": 300, "valid": 288, "invalid": 12}`. Rejects by reason: `implausible` 6, `non_numeric` 4, `unknown_test` 2.
- **74** summary rows. Two have `count` 0: `S02,XYZ` and `S12,LDL`.
- `S01,GLU`: count 16, invalid 2, mean `290.7981`, min 10.0, max 1000.0 (both bounds are inclusive).
- Row 11 has site `" S02"` and row 12 has code `hba1c`: both land in `S02,HBA1C`.

On a generated file: `sum(count) + sum(invalid_count)` equals the number of rows the generator wrote. If it doesn't, you lost rows.

</details>

## Say it out loud

- **Restate:** one sequential pass, O(groups) memory, and every row is accounted for in exactly one group, valid or invalid.
- **Edge cases:** NaN and inf parse as floats, scientific notation, padded values, inclusive bounds, codes in mixed case, a group with no valid rows, unknown codes.
- **Plan:** a running count/sum/min/max per group, rejects written as they stream, the summary written at the end from the small dict.
- **Complexity:** O(n) time, O(g) memory for g groups, plus a constant-size read buffer.
- **Numerics:** a naive sum over billions of rows loses precision. Use `math.fsum` per chunk, Kahan summation, or Welford's algorithm, which also gives you variance in one pass.
- **Median:** an exact median can't be computed in one pass with constant memory (you'd need every value, or a second pass). Options: t-digest or KLL sketches (approximate, mergeable), a fixed-bin histogram over the plausible range (exact counts per bin, approximate within a bin), or an exact answer with a second pass or an external sort. Say which error you can accept.
- **At 100x (200 GB):** split by byte ranges or by file and aggregate per partition. count/sum/min/max (and t-digests) merge associatively, so a map-reduce gives exactly the same answer.
- **Pedestal mapping:** this is the profiling step that feeds quality checks (fill rates, plausibility ranges) before bronze-to-silver. In Glue or Spark it's a `groupBy(site_id, test_code).agg(...)` with `percentile_approx` for the median, which is a sketch, not exact. In dbt it's a test or a model over the Iceberg table, and the plausibility table belongs in a seed so clinicians can review it.
- **Caveat on the test:** tracemalloc only sees Python allocations. pyarrow-backed pandas strings live outside it, so "< 8 MB traced" is a guardrail, not proof. In production you'd watch the container's RSS.
