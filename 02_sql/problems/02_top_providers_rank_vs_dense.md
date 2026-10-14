# 02. Top providers per site: RANK vs. DENSE_RANK

**Timebox: 15 min** · Tables: `encounters` · Write your answer in `02_sql/solutions/02_top_providers_rank_vs_dense.sql`

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

Operations wants the busiest inpatient providers at each site in 2025, for a staffing review.

## Task

Use only `encounters` rows where:
- `encounter_type = 'inpatient'`
- `admit_at >= '2025-01-01'` and `admit_at < '2026-01-01'`
- `provider_id IS NOT NULL`

1. Count those rows per (`site_id`, `provider_id`). That count is `n_inpatient`.
2. Within each `site_id`, rank the providers by `n_inpatient`, highest first, in two ways: `RANK()` as `rnk` and
   `DENSE_RANK()` as `dense_rnk`.
3. Keep a provider when its `n_inpatient` is one of the three highest **distinct** `n_inpatient` values at its
   `site_id`. A tie never pushes a provider out.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | |
| 2 | provider_id | |
| 3 | n_inpatient | rows counted in step 1 |
| 4 | rnk | `RANK()` by `n_inpatient` descending, within the `site_id` |
| 5 | dense_rnk | `DENSE_RANK()` by `n_inpatient` descending, within the `site_id` |

## Check

```powershell
python tasks.py check-sql 02
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Filter with the dense rank, not the plain rank. Four sites have ties that make them differ.
2. Use a `WINDOW w AS (...)` clause so you don't repeat the partition and order twice.
3. 2025 means `admit_at >= '2025-01-01' AND admit_at < '2026-01-01'`. Why is that better than `extract(year ...)`?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Explain ROW_NUMBER vs. RANK vs. DENSE_RANK with the tie 69, 64, 64, 61.
- Why can't you write `WHERE rank() OVER (...) <= 3` directly?

</details>
