# 10. Pivot test codes into columns

**Timebox: 20 min** · Tables: `labs` · Write your answer in `02_sql/solutions/10_pivot_latest_labs.sql`

A data scientist wants one row per patient with each patient's latest 2025 value for a few tests, as columns.

## Task

For site **S03**, using the latest version of each record (problem 08's rule), take each patient's most recent
2025 result (by `collected_at`; ties broken by highest `lab_id`) for `GLU`, `HBA1C`, `CREAT` and `K`, and pivot
them into columns. Include only patients with at least one of those four tests in 2025. Missing tests are NULL.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | |
| 2 | glu | |
| 3 | hba1c | |
| 4 | creat | |
| 5 | k | |

## Check

```powershell
python tasks.py check-sql 10
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Rank within `(patient_id, test_code)`, keep rank 1, then pivot.
2. Pivot with `max(value) FILTER (WHERE test_code = 'GLU') AS glu`, and so on, grouped by patient.
3. Postgres has `crosstab()` in the `tablefunc` extension. Why is the FILTER form usually preferred?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- What if the list of tests isn't known in advance?
- Wide vs. long tables for analytics: when do you pivot, and where (SQL, dbt, pandas)?

</details>
