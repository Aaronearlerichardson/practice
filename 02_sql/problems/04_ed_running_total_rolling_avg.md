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

For every calendar day in 2025, including days with **zero** ED encounters, return the number of ED encounters
(`encounter_type = 'ed'`, by `admit_at` date) at site S10, the running total since Jan 1, and the average daily
count over the 7 calendar days ending on that day. For Jan 1 to Jan 6, average over the days available so far.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | day | `date`, 365 rows |
| 2 | n_ed | 0 on quiet days |
| 3 | running_total | |
| 4 | rolling_7d_avg | rounded to 2 decimals |

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
