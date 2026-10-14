# 14. PERF: rewrite a correlated subquery

**Timebox: 25 min** · Tables: `labs` · Write your answer in `02_sql/solutions/14_perf_correlated_subquery.sql`, `.indexes.sql` and `.answer.md`

## Tables

Database: Postgres `practice` on localhost:5432.

Table: `labs`

```text
+------------------+---------------+--------------------------------------+
| Column Name      | Type          | Notes                                |
+------------------+---------------+--------------------------------------+
| lab_id           | bigint        | primary key; increases in load order |
| patient_id       | integer       |                                      |
| site_id          | text          |                                      |
| source_record_id | text          |                                      |
| test_code        | text          | GLU CREAT HGB K NA ALT HBA1C PLT     |
| value            | numeric(10,2) | can be NULL                          |
| unit             | text          |                                      |
| collected_at     | timestamp     |                                      |
| loaded_at        | timestamp     |                                      |
| load_batch       | text          | e.g. 'S03-2025Q2'                    |
+------------------+---------------+--------------------------------------+
```

Lab results, append-only, exactly as loaded. (site_id, source_record_id) is the site's own record key. When a site corrects a result, it resends the same source_record_id in a later batch with a later loaded_at; the old row stays. Units follow each site's convention (some sites use SI units, one lowercases 'mg/dl').

An analyst flags HbA1c results that are above the patient's own average. It takes several seconds for one site
and one month, and they want to run it for every site and every month. The query is in
`02_sql/solutions/14_perf_correlated_subquery.slow.sql`:

```sql
SELECT l.lab_id, l.patient_id, l.collected_at, l.value,
       (SELECT round(avg(l2.value), 2)
        FROM labs l2
        WHERE l2.patient_id = l.patient_id AND l2.test_code = 'HBA1C') AS patient_avg
FROM labs l
WHERE l.site_id = 'S12'
  AND l.test_code = 'HBA1C'
  AND l.collected_at >= '2025-04-01' AND l.collected_at < '2025-05-01'
  AND l.value > (SELECT avg(l2.value)
                 FROM labs l2
                 WHERE l2.patient_id = l.patient_id AND l2.test_code = 'HBA1C');
```

## Task

**Goal:** rewrite the slow query so it returns exactly the same result, much faster; add indexes if they help;
and explain why, with the plans and timings as evidence. One result row is one S12 HbA1c result from April 2025
whose `value` is above the patient's own average.

The result that must stay identical is the slow query's. It returns one row per `labs` row with
`site_id = 'S12'`, `test_code = 'HBA1C'`, `collected_at >= '2025-04-01'` and `collected_at < '2025-05-01'`, whose
`value` is greater than the patient's average:

- The patient's average is `avg(value)` over every `labs` row with the same `patient_id` and
  `test_code = 'HBA1C'`: all sites, all dates and all versions of each record (no latest-version filter). `avg`
  skips NULL values.
- `value` is compared with the unrounded average. `patient_avg` shows it rounded to 2 decimals.
- A row whose `value` is NULL is never returned (`NULL > x` is not true).

It has 39 rows. The columns are in Output columns below.

You write three files, all in `02_sql/solutions/`:

1. **Diagnose before changing anything.** Run the slow query under `EXPLAIN (ANALYZE, BUFFERS)`: in DataGrip, or
   with `python tasks.py time-sql 02_sql/solutions/14_perf_correlated_subquery.slow.sql` (it runs the query 4
   times, so it takes a while). Find the two `SubPlan` nodes and their `loops=`. In section 1 of
   `14_perf_correlated_subquery.answer.md`, explain in one sentence why the runtime is (loops) x (one full scan of
   `labs`).
2. **Write the rewrite.** Put your query in `14_perf_correlated_subquery.sql`. Compute each patient's average
   once: with a join to a pre-aggregated CTE **or** with a window function. It must return the same rows, with
   the same 5 columns in the same order.
3. **Add indexes if they help.** Put the `CREATE INDEX` statement (or statements) in
   `14_perf_correlated_subquery.indexes.sql`. Name each index `ix_...`. You don't run them yourself: step 4
   does. When the report comes back, notice how much the indexes help even the **slow** query.
4. **Time it.** Run `python tasks.py perf 14`. It drops every non-primary-key index on the practice tables, then
   times four variants: the slow query and your rewrite, each first without and then with your indexes. Each
   variant runs once under `EXPLAIN (ANALYZE, BUFFERS)` and then 3 more times; the median counts. The first
   variant (slow query, no indexes) takes the longest. It checks that your rewrite returns the slow query's
   result, writes the timing table and all four plans to `14_perf_correlated_subquery.report.md`, and drops your
   indexes again.
5. **Explain it.** Fill in sections 2 to 6 of `14_perf_correlated_subquery.answer.md`: the fix, the timing table
   from the report, the plan after, and the 60-second interview answer. This can be its own 10-minute sitting.

## Output columns

Your rewrite returns the slow query's columns, in this order:

| # | column | notes |
|---|---|---|
| 1 | lab_id | `labs.lab_id` |
| 2 | patient_id | `labs.patient_id` |
| 3 | collected_at | `labs.collected_at` |
| 4 | value | `labs.value` (never NULL in the result) |
| 5 | patient_avg | the patient's average HbA1c `value` (defined above), rounded to 2 decimals |

## Check

```powershell
python tasks.py perf 14
```

Done when `perf` prints `Rewrite returns the same result as the slow query: YES` and the answer file is filled
in. Graded by your explanation and the timing comparison (plus that correctness check), not a hash alone.
`python tasks.py check-sql 14` checks only your rewrite's result, without timing.

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. The same correlated subquery appears twice. The WHERE copy runs once per candidate row, and the SELECT copy runs again for every returned row. A CTE computes the average once per patient.
2. Aggregate only the patients you need: `WHERE patient_id IN (SELECT patient_id FROM target)`, where `target` is a CTE holding the S12 April HbA1c rows.
3. Window version: `avg(value) OVER (PARTITION BY patient_id)` over all HbA1c rows, then filter. Compare its plan with the join version. Which scales better to all sites?
4. An index on `(patient_id, test_code) INCLUDE (value)` can make each subplan an index-only scan.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Postgres doesn't decorrelate scalar subqueries; some engines do (e.g. Spark, Snowflake). Why does that matter when you move a query between engines?
- Your rewrite runs in milliseconds. How would you now produce this flag for all sites and months as a dbt model?

</details>
