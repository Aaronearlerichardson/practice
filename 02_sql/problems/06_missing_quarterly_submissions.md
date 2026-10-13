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

List every (site, quarter) with **no accepted load**, and how many rejected attempts the site made for that quarter.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | |
| 2 | quarter_start | `date`, first day of the quarter |
| 3 | rejected_attempts | 0 if the site sent nothing at all |

## Check

```powershell
python tasks.py check-sql 06
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Generate the calendar per site: `CROSS JOIN LATERAL generate_series(date_trunc('quarter', onboarded_on), date '2026-04-01', interval '3 months')`.
2. Anti-join with `NOT EXISTS` (or `LEFT JOIN ... WHERE x IS NULL`). Why is `NOT IN` with a subquery risky?
3. Count rejected attempts with a LEFT JOIN so sites with zero attempts still appear.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- `NOT IN` vs. `NOT EXISTS` when the subquery can return NULL: what goes wrong?
- How would you turn this into an alert that fires N days after a quarter's deadline?

</details>
