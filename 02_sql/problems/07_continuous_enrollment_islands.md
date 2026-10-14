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

Cohort definitions require "continuous enrollment". Sites send enrollment rows that can be adjacent, overlap,
sit entirely inside another row, or have gaps.

## Task

**Goal:** return one row per continuous enrollment period of each `patient_id`: the period's first day, last day
and length in days. A period merges all of one patient's `enrollments` rows that overlap or touch, directly or
through a chain of other rows.

1. **Fill in open-ended rows.** Treat a NULL `end_date` as `2026-06-30` (the patient is still enrolled). Every later
   step uses this filled-in `end_date`.
2. **Find the rows that join.** Work per `patient_id`. Two `enrollments` rows A and B of the same `patient_id` join
   when they:
   - **overlap**: `A.start_date <= B.end_date` and `B.start_date <= A.end_date`, or
   - **touch**: `B.start_date = A.end_date + 1` (B starts the day after A ends).

   Check each pair both ways round: A and B can be either of the two rows.
3. **Follow chains into periods.** Chains count: if A joins B and B joins C, all three are one period, even when A
   and C neither overlap nor touch. Every row belongs to exactly one period, and a row that joins no other row is a
   period on its own.
4. **Describe each period.** For each period, compute:
   - `period_start`: the earliest `start_date` in the period
   - `period_end`: the latest `end_date` in the period (from step 1, so a NULL `end_date` is reported as
     `2026-06-30`)
   - `days`: inclusive, `period_end - period_start + 1`

   Return each period's `patient_id`, `period_start`, `period_end` and `days`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | from step 4: the `patient_id` of the period's rows |
| 2 | period_start | `date` from step 4: the earliest `start_date` in the period |
| 3 | period_end | `date` from step 4: the latest `end_date` in the period, with NULL reported as `2026-06-30` |
| 4 | days | from step 4, inclusive: `period_end - period_start + 1` |

## Example

Input `enrollments` (only the columns this task reads):

```text
+---------------+------------+------------+------------+
| enrollment_id | patient_id | start_date | end_date   |
+---------------+------------+------------+------------+
| 12482         | 100126     | 2023-01-01 | 2023-06-30 |
| 33139         | 100126     | 2023-03-01 | 2023-03-31 |
| 50506         | 100126     | 2023-07-01 | 2023-12-31 |
| 24847         | 100126     | 2023-11-15 | 2024-03-31 |
| 13797         | 100126     | 2024-04-10 | 2024-09-30 |
| 37923         | 100144     | 2024-02-01 | 2024-05-31 |
| 44735         | 100144     | 2024-06-02 | NULL       |
| 59863         | 100144     | 2025-03-01 | 2025-08-31 |
+---------------+------------+------------+------------+
```

Output:

```text
+------------+--------------+------------+------+
| patient_id | period_start | period_end | days |
+------------+--------------+------------+------+
| 100126     | 2023-01-01   | 2024-03-31 | 456  |
| 100126     | 2024-04-10   | 2024-09-30 | 174  |
| 100144     | 2024-02-01   | 2024-05-31 | 121  |
| 100144     | 2024-06-02   | 2026-06-30 | 759  |
+------------+--------------+------------+------+
```

Explanation:

- **Step 1.** enrollment_id 44735 has a NULL `end_date`, so its `end_date` becomes 2026-06-30.
- **Step 2.** Patient 100126: 33139 (2023-03-01 to 2023-03-31) sits entirely inside 12482 (2023-01-01 to
  2023-06-30), so they overlap. 50506 starts 2023-07-01 = 2023-06-30 + 1, so it touches 12482. It does not touch
  33139, which ends earlier, on 2023-03-31. 24847 overlaps 50506: 2023-11-15 <= 2023-12-31 and
  2023-07-01 <= 2024-03-31. 13797 starts 2024-04-10, but 24847 ends 2024-03-31, so 2024-04-01 to 2024-04-09 is a
  gap and 13797 joins nothing. Patient 100144: 44735 starts 2024-06-02, 2 days after 37923 ends (2024-05-31), so
  2024-06-01 is uncovered and they don't touch. 59863 (2025-03-01 to 2025-08-31) sits inside 44735 (2024-06-02 to
  2026-06-30), so they overlap.
- **Step 3.** 12482 joins 33139 and 50506, and 50506 joins 24847, so all four are one period, even though 12482
  and 24847 neither overlap nor touch. 13797 is a period on its own. Patient 100144 has two periods: 37923 alone,
  and 44735 with 59863.
- **Step 4.** 100126's first period: `period_start` = 2023-01-01, `period_end` = 2024-03-31, `days` =
  2024-03-31 - 2023-01-01 + 1 = 455 + 1 = 456. Its second: `days` = 2024-09-30 - 2024-04-10 + 1 = 173 + 1 = 174.
  100144's first: `days` = 2024-05-31 - 2024-02-01 + 1 = 120 + 1 = 121 (2024 is a leap year). Its second has
  `period_end` = 2026-06-30, 44735's filled-in `end_date`, which is later than 59863's 2025-08-31:
  `days` = 2026-06-30 - 2024-06-02 + 1 = 758 + 1 = 759.

The real answer has 51,273 rows, one per continuous period, for 40,000 patients.

## Check

```powershell
python tasks.py check-sql 07
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Order each patient's `enrollments` rows by `start_date`. A new island (period) starts when `start_date > (latest end seen so far) + 1`.
2. "Latest end seen so far" isn't `LAG(end_date)`: a short row inside a long one breaks that. Use `max(end_date) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)` on the filled-in `end_date`.
3. A running `sum()` of the new-island flags gives an island id; then `GROUP BY patient_id, island_id`.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Walk through your solution on: [Jan 1 to Mar 31], [Feb 1 to Feb 10], [Apr 1 to Jun 30], [Jul 5 to Aug 1].
- How would you allow gaps of up to 30 days (a common claims rule)?

</details>
