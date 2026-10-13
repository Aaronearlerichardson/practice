# 13. PERF: rewrite a slow query and add an index

**Timebox: 25 min** · Tables: `labs, sites` · Write your answer in `02_sql/solutions/13_perf_sargable_rewrite.sql`

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

Table: `sites`

```text
+--------------+---------+----------------------------------------+
| Column Name  | Type    | Notes                                  |
+--------------+---------+----------------------------------------+
| site_id      | text    | primary key; 'S01'..'S12'              |
| site_name    | text    |                                        |
| state        | char(2) |                                        |
| ehr_vendor   | text    |                                        |
| onboarded_on | date    | first quarter a site owes a submission |
+--------------+---------+----------------------------------------+
```

One row per contributing health system.

A clinical reviewer's weekly potassium report is slow and the DBA flagged it. The query is in
`02_sql/solutions/13_perf_sargable_rewrite.slow.sql`:

```sql
SELECT l.lab_id, l.patient_id, s.site_name, l.collected_at, l.value, l.unit
FROM labs l
JOIN sites s ON s.site_id = l.site_id
WHERE upper(l.test_code) = 'K'
  AND date_trunc('day', l.collected_at) BETWEEN '2025-03-01' AND '2025-03-07'
ORDER BY l.collected_at DESC;
```

## Task

1. Run it under `EXPLAIN (ANALYZE, BUFFERS)` (DataGrip, or `python tasks.py time-sql 02_sql/solutions/13_perf_sargable_rewrite.slow.sql`). **Before** changing anything, write down which plan node does the work and why no index can help as written.
2. Put the index (or indexes) you'd add in `13_perf_sargable_rewrite.indexes.sql`.
3. Put your rewritten query in `13_perf_sargable_rewrite.sql`. It must return **exactly** the same rows.
4. Run `python tasks.py perf 13`. It drops all your indexes, then times four variants (slow and rewrite, each without and with your indexes), checks that your rewrite returns the same rows, and writes all four plans to `13_perf_sargable_rewrite.report.md`.
5. Fill in `13_perf_sargable_rewrite.answer.md`: plan before and after, the timing table, and the explanation you'd give in an interview.

Graded by your explanation and the timing comparison (plus the correctness check), not a hash alone.
`python tasks.py check-sql 13` also verifies your rewrite's result.

## Check

```powershell
python tasks.py check-sql 13
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Two predicates wrap the column in a function. A B-tree index on `x` can't serve `f(x) = ...`.
2. `date_trunc('day', t) BETWEEN '2025-03-01' AND '2025-03-07'` is equivalent to `t >= '2025-03-01' AND t < '2025-03-08'`. Check the upper end carefully.
3. Index column order: put the equality column first, then the range column. Does the index also give you the ORDER BY for free?
4. Is `upper(test_code) = 'K'` the same as `test_code = 'K'` here? Prove it with a query; say the assumption out loud.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- When would an expression index (`CREATE INDEX ... ((date_trunc('day', collected_at)))`) be the better fix?
- What does the index cost on write? This table takes a quarterly bulk load.

</details>
