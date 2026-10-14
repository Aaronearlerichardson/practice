# 04. ED visits: running total and 7-day rolling average

**Timebox: 20 min** · Tables: `encounters` · Write your answer in `02_sql/solutions/04_ed_running_total_rolling_avg.sql`

## Tables

Database: Postgres `practice` on localhost:5432.

Table: `encounters`

```text
+----------------+-----------+---------------------------------------+
| Column Name    | Type      | Notes                                 |
+----------------+-----------+---------------------------------------+
| encounter_id   | bigint    | primary key                           |
| patient_id     | integer   |                                       |
| site_id        | text      |                                       |
| encounter_type | text      | outpatient, telehealth, ed, inpatient |
| admit_at       | timestamp |                                       |
| discharge_at   | timestamp | can be NULL                           |
| primary_dx     | text      | can be NULL; ICD-10-CM code           |
| provider_id    | text      | can be NULL                           |
+----------------+-----------+---------------------------------------+
```

A capacity dashboard for site **S10** (a small site with quiet days) needs daily ED volume for 2025.

## Task

**Goal:** return one row per calendar day of 2025 (365 rows, including days with no visits) for site `S10`'s ED
visits: the number of visits that day, the running total since 2025-01-01, and the 7-day rolling average of the
daily count.

1. **Keep S10's 2025 ED rows.** From `encounters`, keep the rows where:
   - `site_id = 'S10'`
   - `encounter_type = 'ed'`
   - `admit_at >= '2025-01-01'` and `admit_at < '2026-01-01'`
2. **Build the calendar.** Make one row for every calendar day from 2025-01-01 through 2025-12-31 (365 rows), in a
   `date` column `day`. Every day gets a row, including days with no step 1 rows.
3. **Count each day's visits.** `n_ed` is the number of step 1 rows with `admit_at::date = day`. It is 0 when there
   are none.
4. **Add the running total.** `running_total` is the sum of `n_ed` over every day from 2025-01-01 through `day`,
   including `day`.
5. **Add the 7-day rolling average.** `rolling_7d_avg` is the average of `n_ed` over the 7 days from `day - 6`
   through `day`, rounded to 2 decimals. Days with `n_ed = 0` are among those 7 days and count as 0. For
   2025-01-01 to 2025-01-06, average from 2025-01-01 through `day` instead (so Jan 3 averages 3 days). Return `day`,
   `n_ed`, `running_total` and `rolling_7d_avg`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | day | `date`, from step 2 |
| 2 | n_ed | from step 3; 0 when the day has no step 1 rows |
| 3 | running_total | from step 4 |
| 4 | rolling_7d_avg | from step 5; rounded to 2 decimals |

## Example

Input `encounters` (only the columns this task reads, plus `encounter_id` to name the rows):

```text
+--------------+---------+----------------+---------------------+
| encounter_id | site_id | encounter_type | admit_at            |
+--------------+---------+----------------+---------------------+
| 155650       | S10     | ed             | 2024-12-31 22:15:03 |
| 155787       | S10     | ed             | 2025-01-01 03:18:10 |
| 155812       | S10     | ed             | 2025-01-01 09:42:51 |
| 155904       | S10     | ed             | 2025-01-01 12:23:17 |
| 156197       | S10     | ed             | 2025-01-02 15:20:38 |
| 156231       | S10     | inpatient      | 2025-01-02 18:04:12 |
| 156602       | S03     | ed             | 2025-01-04 10:31:22 |
| 156696       | S10     | ed             | 2025-01-04 20:46:03 |
| 156713       | S10     | ed             | 2025-01-04 23:58:35 |
| 156763       | S10     | ed             | 2025-01-05 10:02:58 |
| 157354       | S10     | ed             | 2025-01-07 14:29:01 |
+--------------+---------+----------------+---------------------+
```

Output (this example uses an 8-day calendar, 2025-01-01 through 2025-01-08, to stay short):

```text
+------------+------+---------------+----------------+
| day        | n_ed | running_total | rolling_7d_avg |
+------------+------+---------------+----------------+
| 2025-01-01 | 3    | 3             | 3.00           |
| 2025-01-02 | 1    | 4             | 2.00           |
| 2025-01-03 | 0    | 4             | 1.33           |
| 2025-01-04 | 2    | 6             | 1.50           |
| 2025-01-05 | 1    | 7             | 1.40           |
| 2025-01-06 | 0    | 7             | 1.17           |
| 2025-01-07 | 1    | 8             | 1.14           |
| 2025-01-08 | 0    | 8             | 0.71           |
+------------+------+---------------+----------------+
```

Explanation:

- **Step 1.** Three rows are dropped: 155650 (`admit_at` is in 2024), 156231 (`inpatient`) and 156602 (`site_id`
  is `S03`). The other 8 rows stay.
- **Step 2.** To keep the example short, its calendar runs from 2025-01-01 through 2025-01-08 (8 days) instead of
  all 365 days. Jan 3, Jan 6 and Jan 8 have no step 1 rows but still get a row.
- **Step 3.** Jan 1 has 3 (155787, 155812, 155904). Jan 2 has 1 (156197). Jan 4 has 2 (156696, 156713; 23:58:35
  is still Jan 4). Jan 5 has 1 (156763). Jan 7 has 1 (157354). Jan 3, Jan 6 and Jan 8 have 0.
- **Step 4.** 3, then 3 + 1 = 4, 4 + 0 = 4, 4 + 2 = 6, 6 + 1 = 7, 7 + 0 = 7, 7 + 1 = 8, 8 + 0 = 8.
- **Step 5.** Jan 1 to Jan 6 average from Jan 1 only: Jan 1 = 3 / 1 = 3.00, Jan 2 = (3 + 1) / 2 = 2.00, Jan 3 =
  (3 + 1 + 0) / 3 = 1.33, Jan 4 = 6 / 4 = 1.50, Jan 5 = 7 / 5 = 1.40, Jan 6 = 7 / 6 = 1.17. The 2024-12-31 visit
  never enters an average. Jan 7 is the first full 7-day window (Jan 1 to Jan 7): 8 / 7 = 1.14. Jan 8 covers Jan 2
  to Jan 8, so Jan 1's 3 visits leave the window: (1 + 0 + 2 + 1 + 0 + 1 + 0) / 7 = 5 / 7 = 0.71.

The real answer has 365 rows, one per day of 2025.

## Check

```powershell
python tasks.py check-sql 04
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. `generate_series(date '2025-01-01', date '2025-12-31', interval '1 day')` gives you the calendar.
2. What does `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` mean when some days are missing from the input?
3. Postgres also supports `RANGE BETWEEN interval '6 days' PRECEDING AND CURRENT ROW`. When would that save you the calendar?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- ROWS vs. RANGE frames: what's the default frame when you write only `ORDER BY`, and why does it matter with ties?
- How would you compute this for all 12 sites in one query?

</details>
