# 11. Median and percentiles per test

**Timebox: 20 min** · Tables: `labs` · Write your answer in `02_sql/solutions/11_lab_percentiles.sql`

For a reference-range sanity check, compute distribution statistics per test.

## Task

Using the latest version of each record (problem 08's rule, all sites), keep only rows whose unit equals the
test's canonical unit, **case-insensitively** (canonical units are in problem 09's table, plus K and NA `mmol/L`,
ALT `U/L`, HBA1C `%`, PLT `10*3/uL`), with a non-NULL value. Per test, return:

## Output columns

| # | column | notes |
|---|---|---|
| 1 | test_code | 8 rows |
| 2 | n | rows used |
| 3 | p10 | `percentile_disc(0.10)` |
| 4 | median | `percentile_cont(0.50)` |
| 5 | p90 | `percentile_disc(0.90)` |
| 6 | mean | rounded to 2 decimals |

## Check

```powershell
python tasks.py check-sql 11
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. `percentile_cont(0.5) WITHIN GROUP (ORDER BY value)` is an ordered-set aggregate: it goes in the SELECT with GROUP BY.
2. A canon `(test_code, unit)` VALUES list joined on `lower(unit)` is cleaner than a long CASE.
3. Check `n` against a version without the unit filter. How many rows does the unit filter drop, and from which site?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- percentile_cont vs. percentile_disc: what's the difference, and when does it matter?
- Mean vs. median for lab values: why might they disagree here? (Look at problem 09's violations.)
- How would you compute an approximate median over billions of rows?

</details>
