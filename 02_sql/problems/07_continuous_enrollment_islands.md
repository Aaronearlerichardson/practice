# 07. Gaps and islands: continuous enrollment periods

**Timebox: 25 min** · Tables: `enrollments` · Write your answer in `02_sql/solutions/07_continuous_enrollment_islands.sql`

Cohort definitions require "continuous enrollment". Sites send enrollment periods that can be adjacent, overlap,
sit entirely inside another period, or have gaps.

## Task

Merge each patient's enrollment periods into **continuous periods**. Two periods belong to the same continuous
period if they overlap or if one starts the day after the other ends. A `NULL` `end_date` means still enrolled:
treat it as `2026-06-30`, and report it as `2026-06-30`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | |
| 2 | period_start | `date` |
| 3 | period_end | `date` |
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
