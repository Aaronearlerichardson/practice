# 05. Fill rate per column per site

**Timebox: 20 min** · Tables: `patients` · Write your answer in `02_sql/solutions/05_demographic_fill_rates.sql`

A data quality report needs demographic **fill rates** per site. Sites encode "missing" differently: some send
NULL, some an empty string, some a placeholder.

## Task

For each site and each of the columns `birth_date, sex, race, ethnicity, zip3`, compute the percent of patients
whose value is **filled**. A value is NOT filled if it is NULL, an empty string `''`, or a placeholder: `'U'`
for sex, `'Unknown'` for race and ethnicity (exact, case-sensitive match).

Return one row per (site, column): a long format that's easy to chart and threshold.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | |
| 2 | column_name | one of `birth_date, sex, race, ethnicity, zip3` |
| 3 | fill_pct | 0 to 100, rounded to 2 decimals |

## Check

```powershell
python tasks.py check-sql 05
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. `count(col)` ignores NULLs but not `''`. `count(*) FILTER (WHERE ...)` lets you write any rule.
2. Unpivot with `CROSS JOIN LATERAL (VALUES ('sex', <is filled>), ...) AS v(column_name, filled)`.
3. `zip3` is `char(3)`: compare with `coalesce(zip3, '') <> ''`.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- This report will run every quarter on every table. How would you generate it instead of hand-writing every column?
- Which sites fall below 90% on which columns? What would you tell the site liaison?

</details>
