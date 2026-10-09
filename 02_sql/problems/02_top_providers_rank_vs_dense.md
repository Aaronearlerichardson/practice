# 02. Top providers per site: RANK vs. DENSE_RANK

**Timebox: 15 min** · Tables: `encounters` · Write your answer in `02_sql/solutions/02_top_providers_rank_vs_dense.sql`

Operations wants the busiest inpatient providers at each site in 2025, for a staffing review.

## Task

Count inpatient encounters (`encounter_type = 'inpatient'`) admitted in calendar year 2025, per site and provider.
Ignore encounters with no `provider_id`. Within each site, rank providers by that count, highest first.
Keep every provider in the **top three distinct count levels**, so ties never push anyone out, and report both
kinds of rank so the difference is visible.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | |
| 2 | provider_id | |
| 3 | n_inpatient | |
| 4 | rnk | `RANK()` within the site |
| 5 | dense_rnk | `DENSE_RANK()` within the site |

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
