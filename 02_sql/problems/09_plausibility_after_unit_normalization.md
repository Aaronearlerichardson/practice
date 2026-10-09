# 09. Plausibility violations after unit normalization

**Timebox: 25 min** · Tables: `labs` · Write your answer in `02_sql/solutions/09_plausibility_after_unit_normalization.sql`

Medical plausibility checks only make sense in one unit system. Some sites report SI units, and one site
lowercases units (`mg/dl`).

## Task

Using only the **latest version** of each record (problem 08's rule, all sites) with a non-NULL value,
normalize each value to the canonical unit, then return the rows outside the plausible range.

Unit comparison is **case-insensitive**. Conversions (apply exactly these):

| test_code | canonical unit | convert from | formula |
|---|---|---|---|
| GLU | mg/dL | mmol/L | `value * 18` |
| CREAT | mg/dL | umol/L | `value / 88.4` |
| HGB | g/dL | g/L | `value / 10` |
| others | as stored | | no conversion |

Plausible ranges (inclusive, canonical units): GLU 20-1000, CREAT 0.1-20, HGB 3-25, K 1.5-9, NA 100-180,
ALT 1-5000, HBA1C 3-20, PLT 1-2000. Compare the **unrounded** normalized value; round only for output.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | lab_id | |
| 2 | site_id | |
| 3 | test_code | |
| 4 | value | as stored |
| 5 | unit | as stored |
| 6 | normalized_value | rounded to 2 decimals |
| 7 | reason | `'below_range'` or `'above_range'` |

## Check

```powershell
python tasks.py check-sql 09
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Build it in CTEs: latest, then normalized, then a `ranges(test_code, low, high) AS (VALUES ...)` CTE, then join.
2. A `CASE` on `(test_code, lower(unit))` does the conversion.
3. Sanity check: count violations per site and reason. Does any site stand out? Why?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Where would this rule live in the stack: a dbt test, a Great Expectations suite, or a silver-model column? Trade-offs?
- Hard-coding conversions in SQL vs. a seed/reference table: which, and why?

</details>
