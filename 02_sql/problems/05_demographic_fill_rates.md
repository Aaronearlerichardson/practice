# 05. Fill rate per column per site

**Timebox: 20 min** · Tables: `patients` · Write your answer in `02_sql/solutions/05_demographic_fill_rates.sql`

## Tables

Database: Postgres `practice` on localhost:5432.

Table: `patients`

```text
+-------------+---------+-------------------------------------+
| Column Name | Type    | Notes                               |
+-------------+---------+-------------------------------------+
| patient_id  | integer | primary key                         |
| site_id     | text    |                                     |
| birth_date  | date    | can be NULL                         |
| sex         | text    | can be NULL; 'F','M','U','' or NULL |
| race        | text    | can be NULL                         |
| ethnicity   | text    | can be NULL                         |
| zip3        | char(3) | can be NULL                         |
+-------------+---------+-------------------------------------+
```

Patient demographics as delivered by the site. Fill rates vary by site: missing values arrive as NULL, '' or 'Unknown'/'U' depending on the site.

A data quality report needs demographic **fill rates** per site. Sites encode "missing" differently: some send
NULL, some an empty string, some a placeholder.

## Task

For each `site_id` in `patients`, and each of the columns `birth_date`, `sex`, `race`, `ethnicity` and `zip3`,
compute:

`fill_pct = 100 * (rows at that site_id where the column is filled) / (all rows at that site_id)`, rounded to 2
decimals.

A column's value is **not filled** when it is:
- NULL, or
- the empty string `''` (applies to `sex`, `race`, `ethnicity` and `zip3`), or
- a placeholder, matched exactly and case-sensitively: `sex = 'U'`, `race = 'Unknown'`, `ethnicity = 'Unknown'`.

`birth_date` is a `date`, so only NULL counts as not filled there. Every other value counts as filled.

Return one row per (`site_id`, column): a long format that's easy to chart and threshold.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | |
| 2 | column_name | the text `'birth_date'`, `'sex'`, `'race'`, `'ethnicity'` or `'zip3'` |
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
