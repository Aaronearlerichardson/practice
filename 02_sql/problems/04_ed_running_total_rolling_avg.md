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

Use only `encounters` rows where:
- `site_id = 'S10'`
- `encounter_type = 'ed'`
- `admit_at >= '2025-01-01'` and `admit_at < '2026-01-01'`

Return one row for every calendar day from 2025-01-01 through 2025-12-31 (365 rows), including days with no
matching rows.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | day | `date` |
| 2 | n_ed | number of rows with `admit_at::date = day`; 0 when there are none |
| 3 | running_total | sum of `n_ed` from 2025-01-01 through `day` |
| 4 | rolling_7d_avg | average of `n_ed` from `day - 6` through `day`, rounded to 2 decimals. For 2025-01-01 to 2025-01-06, average from 2025-01-01 through `day` instead (so Jan 3 averages 3 days). |

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
