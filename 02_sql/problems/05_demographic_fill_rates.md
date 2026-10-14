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

**Goal:** return one row per (`site_id`, column) pair: for each site and each of the five demographic columns
`birth_date`, `sex`, `race`, `ethnicity` and `zip3`, the percentage of that site's `patients` rows where the column
is filled. This long format is easy to chart and threshold.

1. **Decide whether each value is filled.** Check each of the five columns on every `patients` row. A value is
   **not filled** when it is:
   - NULL, or
   - the empty string `''` (applies to `sex`, `race`, `ethnicity` and `zip3`), or
   - a placeholder, matched exactly and case-sensitively: `sex = 'U'`, `race = 'Unknown'`, `ethnicity = 'Unknown'`.

   `birth_date` is a `date`, so only NULL counts as not filled there. Every other value counts as filled, including
   a placeholder in another case, such as `race = 'unknown'`.
2. **Count the rows per site.** Group the `patients` rows by `site_id`. For each `site_id` and each of the five
   columns, count `filled_rows`, the site's rows where that column is filled (step 1), and `all_rows`, all of the
   site's rows. `all_rows` is the same for all five columns.
3. **Compute the fill rate.** Return one row per (`site_id`, column) with:
   - `column_name`: the column's name as text: `'birth_date'`, `'sex'`, `'race'`, `'ethnicity'` or `'zip3'`
   - `fill_pct`: `100 * filled_rows / all_rows`, rounded to 2 decimals

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | `patients.site_id` |
| 2 | column_name | from step 3: the text `'birth_date'`, `'sex'`, `'race'`, `'ethnicity'` or `'zip3'` |
| 3 | fill_pct | from step 3: 0 to 100, rounded to 2 decimals |

## Example

Input `patients` (only the columns this task reads; `''` is the empty string):

```text
+------------+---------+------------+-----+---------------------------+------------------------+------+
| patient_id | site_id | birth_date | sex | race                      | ethnicity              | zip3 |
+------------+---------+------------+-----+---------------------------+------------------------+------+
| 100003     | S03     | 1970-04-30 | M   | Black or African American | NULL                   | 224  |
| 100007     | S03     | 1995-10-22 | U   | Unknown                   | NULL                   | NULL |
| 100013     | S03     | 1992-07-28 | F   | Unknown                   | NULL                   | 237  |
| 100039     | S03     | NULL       | F   | unknown                   | Hispanic or Latino     | 241  |
| 100002     | S05     | 2005-06-30 | M   | White                     | ''                     | 275  |
| 100006     | S05     | 2005-02-19 | ''  | Black or African American | Not Hispanic or Latino | 287  |
| 100012     | S05     | 2000-03-18 | F   | NULL                      | Unknown                | ''   |
+------------+---------+------------+-----+---------------------------+------------------------+------+
```

Output:

```text
+---------+-------------+----------+
| site_id | column_name | fill_pct |
+---------+-------------+----------+
| S03     | birth_date  | 75.00    |
| S03     | sex         | 75.00    |
| S03     | race        | 50.00    |
| S03     | ethnicity   | 25.00    |
| S03     | zip3        | 75.00    |
| S05     | birth_date  | 100.00   |
| S05     | sex         | 66.67    |
| S05     | race        | 66.67    |
| S05     | ethnicity   | 33.33    |
| S05     | zip3        | 66.67    |
+---------+-------------+----------+
```

Explanation:

- **Step 1.** At `S03`, these values are not filled: 100039's `birth_date` (NULL), 100007's `sex` (`'U'`), the
  `race` of 100007 and 100013 (`'Unknown'`), the `ethnicity` of 100003, 100007 and 100013 (NULL), and 100007's
  `zip3` (NULL). 100039's `race = 'unknown'` is filled: the placeholder match is case-sensitive, and `'unknown'` is
  not `'Unknown'`. At `S05`, these are not filled: 100006's `sex` (`''`), 100012's `race` (NULL), 100002's
  `ethnicity` (`''`), 100012's `ethnicity` (`'Unknown'`) and 100012's `zip3` (`''`).
- **Step 2.** `S03` has `all_rows` = 4, with `filled_rows` of 3 (`birth_date`), 3 (`sex`), 2 (`race`),
  1 (`ethnicity`) and 3 (`zip3`). `S05` has `all_rows` = 3, with `filled_rows` of 3, 2, 2, 1 and 2.
- **Step 3.** `S03`: `birth_date` = 100 * 3 / 4 = 75.00, `race` = 100 * 2 / 4 = 50.00, `ethnicity` =
  100 * 1 / 4 = 25.00. `S05`: `birth_date` = 100 * 3 / 3 = 100.00, `sex` = 100 * 2 / 3 = 66.666... -> 66.67,
  `ethnicity` = 100 * 1 / 3 = 33.333... -> 33.33.

The real answer has 60 rows: 12 sites x 5 columns.

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
