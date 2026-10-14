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

**Goal:** return one row per (`site_id`, `provider_id`) for the busiest inpatient providers at each site in 2025:
the provider's number of 2025 inpatient encounters and two ranks of that number within the site. Keep only
providers whose count is one of the three highest distinct counts at their site.

1. **Keep 2025 inpatient rows with a provider.** From `encounters`, keep the rows where:
   - `encounter_type = 'inpatient'`
   - `admit_at >= '2025-01-01'` and `admit_at < '2026-01-01'`
   - `provider_id IS NOT NULL`
2. **Count per provider.** Count the step 1 rows per (`site_id`, `provider_id`). That count is `n_inpatient`.
3. **Rank the providers two ways.** Within each `site_id`, order the providers by `n_inpatient`, highest first, and
   compute two ranks. Providers at different sites are never compared.
   - `rnk`: `RANK()` by `n_inpatient` descending. Providers with the same `n_inpatient` share a rank, and the next
     rank skips past the tie.
   - `dense_rnk`: `DENSE_RANK()` by `n_inpatient` descending. Providers with the same `n_inpatient` share a rank,
     and the next rank does not skip.
4. **Keep the three highest distinct counts.** Keep a provider when its `n_inpatient` is one of the three highest
   **distinct** `n_inpatient` values at its `site_id`. A tie never pushes a provider out. Return `site_id`,
   `provider_id`, `n_inpatient`, `rnk` and `dense_rnk`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | from step 2 |
| 2 | provider_id | from step 2 |
| 3 | n_inpatient | step 1 rows counted in step 2 |
| 4 | rnk | from step 3: `RANK()` by `n_inpatient` descending, within the `site_id` |
| 5 | dense_rnk | from step 3: `DENSE_RANK()` by `n_inpatient` descending, within the `site_id` |

## Example

Input `encounters` (only the columns this task reads, plus `encounter_id` to name the rows):

```text
+--------------+---------+----------------+---------------------+-------------+
| encounter_id | site_id | encounter_type | admit_at            | provider_id |
+--------------+---------+----------------+---------------------+-------------+
| 140112       | S09     | inpatient      | 2025-01-14 08:10:00 | S09-PR03    |
| 140530       | S09     | inpatient      | 2025-02-03 21:40:00 | S09-PR07    |
| 140861       | S04     | inpatient      | 2025-02-20 16:05:00 | S04-PR01    |
| 141208       | S09     | inpatient      | 2025-03-11 06:25:00 | S09-PR11    |
| 141877       | S09     | inpatient      | 2025-04-19 13:05:00 | S09-PR03    |
| 142301       | S09     | outpatient     | 2025-05-02 10:30:00 | S09-PR02    |
| 142455       | S09     | inpatient      | 2025-05-09 17:45:00 | S09-PR02    |
| 142960       | S09     | inpatient      | 2025-06-07 02:15:00 | S09-PR07    |
| 143418       | S09     | inpatient      | 2025-07-01 11:50:00 | S09-PR03    |
| 143799       | S09     | inpatient      | 2025-07-22 19:20:00 | NULL        |
| 144236       | S09     | inpatient      | 2025-08-16 04:35:00 | S09-PR11    |
| 144710       | S09     | inpatient      | 2025-09-12 15:55:00 | S09-PR05    |
| 145133       | S09     | inpatient      | 2025-10-04 09:00:00 | S09-PR02    |
| 145587       | S09     | inpatient      | 2025-10-30 22:10:00 | S09-PR11    |
| 146042       | S09     | inpatient      | 2025-11-24 12:40:00 | S09-PR07    |
| 146498       | S09     | inpatient      | 2025-12-19 07:30:00 | S09-PR03    |
| 147011       | S09     | inpatient      | 2026-01-01 00:00:00 | S09-PR05    |
+--------------+---------+----------------+---------------------+-------------+
```

Output:

```text
+---------+-------------+-------------+-----+-----------+
| site_id | provider_id | n_inpatient | rnk | dense_rnk |
+---------+-------------+-------------+-----+-----------+
| S04     | S04-PR01    | 1           | 1   | 1         |
| S09     | S09-PR03    | 4           | 1   | 1         |
| S09     | S09-PR07    | 3           | 2   | 2         |
| S09     | S09-PR11    | 3           | 2   | 2         |
| S09     | S09-PR02    | 2           | 4   | 3         |
+---------+-------------+-------------+-----+-----------+
```

Explanation:

- **Step 1.** Three rows are dropped: 142301 (`outpatient`), 143799 (NULL `provider_id`) and 147011 (`admit_at` is
  2026-01-01 00:00:00, which is not `< '2026-01-01'`). The other 14 rows stay.
- **Step 2.** At S09: S09-PR03 has 4 rows (140112, 141877, 143418, 146498), S09-PR07 has 3, S09-PR11 has 3,
  S09-PR02 has 2 (its outpatient row does not count) and S09-PR05 has 1 (its 2026 row does not count). At S04:
  S04-PR01 has 1.
- **Step 3.** At S09, the counts in order are 4, 3, 3, 2, 1. `rnk` is 1, 2, 2, 4, 5: the two providers with 3 share
  rank 2, so rank 3 is skipped. `dense_rnk` is 1, 2, 2, 3, 4: no rank is skipped. S04 is ranked on its own, so
  S04-PR01 is rank 1 there even though its count (1) is the lowest in the example.
- **Step 4.** S09's distinct counts are 4, 3, 2 and 1, so the three highest are 4, 3 and 2. S09-PR02 (2) is kept
  even though its `rnk` is 4: the tie at 3 does not push it out. S09-PR05 (1) is dropped. S04 has only one distinct
  count (1), so S04-PR01 is kept.

The real answer has 40 rows across the 12 sites.

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
