# 14. PERF: rewrite a correlated subquery

**Timebox: 25 min** · Tables: `labs` · Write your answer in `02_sql/solutions/14_perf_correlated_subquery.sql`

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

1. `EXPLAIN (ANALYZE, BUFFERS)` the slow query. Find the `SubPlan` nodes and their `loops=`. Explain in one sentence why the runtime is (outer rows) x (full table scan).
2. Rewrite it as a join to a pre-aggregated CTE **or** with a window function, in `14_perf_correlated_subquery.sql`. It must return exactly the same rows.
3. Add indexes in `14_perf_correlated_subquery.indexes.sql` if they help. Notice how much the indexes help even the **original** query.
4. Run `python tasks.py perf 14` and fill in `14_perf_correlated_subquery.answer.md`.

## Check

```powershell
python tasks.py check-sql 14
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. The same correlated subquery appears twice, so it runs twice per row. A CTE computes it once per patient.
2. Aggregate only the patients you need: `WHERE patient_id IN (SELECT patient_id FROM target)`.
3. Window version: `avg(value) OVER (PARTITION BY patient_id)` over all HbA1c rows, then filter. Compare its plan with the join version. Which scales better to all sites?
4. An index on `(patient_id, test_code) INCLUDE (value)` can make each subplan an index-only scan.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Postgres doesn't decorrelate scalar subqueries; some engines do (e.g. Spark, Snowflake). Why does that matter when you move a query between engines?
- Your rewrite runs in milliseconds. How would you now produce this flag for all sites and months as a dbt model?

</details>
