# 06. Sites missing a quarterly submission

**Timebox: 20 min** · Tables: `sites, quarterly_loads` · Write your answer in `02_sql/solutions/06_missing_quarterly_submissions.sql`

## Tables

Database: Postgres `practice` on localhost:5432.

Table: `sites`

```text
+--------------+---------+----------------------------------------+
| Column Name  | Type    | Notes                                  |
+--------------+---------+----------------------------------------+
| site_id      | text    | primary key; 'S01'..'S12'              |
| site_name    | text    |                                        |
| state        | char(2) |                                        |
| ehr_vendor   | text    |                                        |
| onboarded_on | date    | first quarter a site owes a submission |
+--------------+---------+----------------------------------------+
```

One row per contributing health system.

Table: `quarterly_loads`

```text
+---------------+-----------+------------------------------------------+
| Column Name   | Type      | Notes                                    |
+---------------+-----------+------------------------------------------+
| load_id       | integer   | primary key                              |
| site_id       | text      |                                          |
| quarter_start | date      | first day of the quarter the data covers |
| received_at   | timestamp |                                          |
| status        | text      | accepted, rejected                       |
| row_count     | integer   |                                          |
+---------------+-----------+------------------------------------------+
```

One row per file delivery attempt. A site-quarter can have a rejected attempt followed by an accepted one, or no row at all.

Each site owes one accepted file per quarter, from the quarter it was onboarded (`sites.onboarded_on`) through
**2026 Q2** (quarter starting 2026-04-01). A rejected file doesn't count as a submission.

## Task

**Goal:** return one row per (`site_id`, `quarter_start`) pair where the site owed a file but `quarterly_loads` has
no accepted file, with the number of rejected attempts for that quarter. A site owes one accepted file per quarter,
from the quarter that contains its `sites.onboarded_on` through 2026 Q2 (`quarter_start = '2026-04-01'`).

1. **List the quarters each site owes.** For each `site_id` in `sites`, list every quarter from
   `date_trunc('quarter', onboarded_on)` through `2026-04-01`, inclusive, as `quarter_start` (a `date`, the first
   day of each quarter). `date_trunc('quarter', onboarded_on)` is the first day of the quarter that contains
   `onboarded_on`, so a site onboarded mid-quarter owes that quarter too. 2026-04-01 is the latest `quarter_start`
   in `quarterly_loads`.
2. **Keep the quarters with no accepted file.** Keep a (`site_id`, `quarter_start`) pair from step 1 when
   `quarterly_loads` has **no** row with that `site_id`, that `quarter_start` and `status = 'accepted'`. A rejected
   file doesn't count as a submission.
3. **Count the rejected attempts.** For each kept pair, `rejected_attempts` is the number of `quarterly_loads` rows
   with that `site_id`, that `quarter_start` and `status = 'rejected'`. It is 0 when there are none. Return each
   kept pair with its `rejected_attempts`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | from step 1 (`sites.site_id`) |
| 2 | quarter_start | `date` from step 1, first day of the quarter |
| 3 | rejected_attempts | from step 3; 0 if the site sent nothing for that quarter |

## Example

Input `sites` (only the columns this task reads):

```text
+---------+--------------+
| site_id | onboarded_on |
+---------+--------------+
| S11     | 2025-08-15   |
| S12     | 2025-10-01   |
+---------+--------------+
```

Input `quarterly_loads` (only the columns this task reads):

```text
+---------+---------+---------------+----------+
| load_id | site_id | quarter_start | status   |
+---------+---------+---------------+----------+
| 95      | S11     | 2025-04-01    | rejected |
| 110     | S11     | 2025-10-01    | rejected |
| 112     | S11     | 2025-10-01    | accepted |
| 113     | S12     | 2025-10-01    | accepted |
| 120     | S11     | 2026-01-01    | rejected |
| 123     | S11     | 2026-01-01    | rejected |
| 125     | S12     | 2026-01-01    | accepted |
| 131     | S11     | 2026-04-01    | accepted |
| 135     | S12     | 2026-04-01    | rejected |
+---------+---------+---------------+----------+
```

Output:

```text
+---------+---------------+-------------------+
| site_id | quarter_start | rejected_attempts |
+---------+---------------+-------------------+
| S11     | 2025-07-01    | 0                 |
| S11     | 2026-01-01    | 2                 |
| S12     | 2026-04-01    | 1                 |
+---------+---------------+-------------------+
```

Explanation:

- **Step 1.** `S11` was onboarded mid-quarter, on 2025-08-15. `date_trunc('quarter', onboarded_on)` = 2025-07-01,
  so `S11` owes 2025-07-01, 2025-10-01, 2026-01-01 and 2026-04-01. `S12` owes 2025-10-01, 2026-01-01 and
  2026-04-01. That is 7 pairs. load_id 95 (`S11`, 2025-04-01) is for a quarter before `S11`'s first one, so no pair
  uses it.
- **Step 2.** Four pairs have an accepted row and are dropped: (`S11`, 2025-10-01) has load_id 112, so the earlier
  rejected load_id 110 doesn't matter; (`S11`, 2026-04-01) has 131; (`S12`, 2025-10-01) has 113; and
  (`S12`, 2026-01-01) has 125. Three pairs are kept.
- **Step 3.** (`S11`, 2025-07-01) has no `quarterly_loads` rows at all, so `rejected_attempts` = 0.
  (`S11`, 2026-01-01) has load_id 120 and 123, both rejected: 2. (`S12`, 2026-04-01) has load_id 135, rejected: 1.

The real answer has 7 rows.

## Check

```powershell
python tasks.py check-sql 06
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Generate the calendar per site: `CROSS JOIN LATERAL generate_series(date_trunc('quarter', onboarded_on), date '2026-04-01', interval '3 months')`.
2. Anti-join with `NOT EXISTS` (or `LEFT JOIN ... WHERE x IS NULL`). Why is `NOT IN` with a subquery risky?
3. Count rejected attempts with a LEFT JOIN so a quarter with no rejected rows still appears, with 0.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- `NOT IN` vs. `NOT EXISTS` when the subquery can return NULL: what goes wrong?
- How would you turn this into an alert that fires N days after a quarter's deadline?

</details>
