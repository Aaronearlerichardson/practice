# 07. Gaps and islands: continuous enrollment periods

**Timebox: 25 min** · Tables: `enrollments` · Write your answer in `02_sql/solutions/07_continuous_enrollment_islands.sql`

## Tables

Database: Postgres `practice` on localhost:5432.

Table: `enrollments`

```text
+---------------+---------+-------------+
| Column Name   | Type    | Notes       |
+---------------+---------+-------------+
| enrollment_id | integer | primary key |
| patient_id    | integer |             |
| site_id       | text    |             |
| start_date    | date    |             |
| end_date      | date    | can be NULL |
+---------------+---------+-------------+
```

Coverage periods at a site. Periods for one patient can be adjacent, overlapping, or separated by gaps. end_date NULL = still enrolled.

Cohort definitions require "continuous enrollment". Sites send enrollment periods that can be adjacent, overlap,
sit entirely inside another period, or have gaps.

## Task

Work per `patient_id`. Treat a NULL `end_date` as `2026-06-30`.

Merge each patient's `enrollments` rows into continuous periods. Two rows A and B are in the same period when they:
- **overlap**: `A.start_date <= B.end_date` and `B.start_date <= A.end_date`, or
- **touch**: `B.start_date = A.end_date + 1` (B starts the day after A ends).

Chains count: if A joins B and B joins C, all three are one period, even when A and C neither overlap nor touch.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | |
| 2 | period_start | `date`: the earliest `start_date` in the period |
| 3 | period_end | `date`: the latest `end_date` in the period, with NULL reported as `2026-06-30` |
| 4 | days | inclusive: `period_end - period_start + 1` |

## Check

```powershell
python tasks.py check-sql 07
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Order each patient's periods by `start_date`. A new island starts when `start_date > (latest end seen so far) + 1`.
2. "Latest end seen so far" isn't `LAG(end_date)`: a short period inside a long one breaks that. Use `max(end_date) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)`.
3. A running `sum()` of the new-island flags gives an island id; then `GROUP BY patient_id, island_id`.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Walk through your solution on: [Jan 1 to Mar 31], [Feb 1 to Feb 10], [Apr 1 to Jun 30], [Jul 5 to Aug 1].
- How would you allow gaps of up to 30 days (a common claims rule)?

</details>
