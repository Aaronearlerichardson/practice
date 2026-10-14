# 13. PERF: rewrite a slow query and add an index

**Timebox: 25 min** · Tables: `labs`, `sites` · Write your answer in `02_sql/solutions/13_perf_sargable_rewrite.sql`, `.indexes.sql` and `.answer.md`

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

**Goal:** rewrite the slow query so it returns exactly the same result, much faster; add the index (or indexes)
that make it fast; and explain why, with the plans and timings as evidence. One result row is one potassium
result collected in the first week of March 2025, with its site's name.

The result that must stay identical is the slow query's: one row per `labs` row with `upper(test_code) = 'K'`
whose `collected_at` falls on a calendar day from 2025-03-01 through 2025-03-07 (both days included, any time of
day), with `site_name` from the `sites` row with the same `site_id`, newest `collected_at` first. It has 1198 rows.
The columns are in Output columns below.

You write three files, all in `02_sql/solutions/`:

1. **Diagnose before changing anything.** Run the slow query under `EXPLAIN (ANALYZE, BUFFERS)`: in DataGrip, or
   with `python tasks.py time-sql 02_sql/solutions/13_perf_sargable_rewrite.slow.sql`. In section 1 of
   `13_perf_sargable_rewrite.answer.md`, write down the plan node that does the work, rows scanned vs. rows
   returned, and why an index on `test_code` or `collected_at` can't help the query as written.
2. **Write the indexes.** Put the `CREATE INDEX` statement (or statements) you'd add in
   `13_perf_sargable_rewrite.indexes.sql`. Name each index `ix_...`. You don't run them yourself: step 4 does.
3. **Write the rewrite.** Put your query in `13_perf_sargable_rewrite.sql`. It must return the same rows, with the
   same 6 columns in the same order. Keep the `ORDER BY collected_at DESC`: the check ignores row order, but the
   reviewer reads newest first, and a rewrite without the sort would not be a fair timing.
4. **Time it.** Run `python tasks.py perf 13`. It drops every non-primary-key index on the practice tables, then
   times four variants: the slow query and your rewrite, each first without and then with your indexes. Each
   variant runs once under `EXPLAIN (ANALYZE, BUFFERS)` and then 3 more times; the median counts. It checks that
   your rewrite returns the slow query's result, writes the timing table and all four plans to
   `13_perf_sargable_rewrite.report.md`, and drops your indexes again.
5. **Explain it.** Fill in sections 2 to 6 of `13_perf_sargable_rewrite.answer.md`: the fix, the timing table
   from the report, the plan after, and the 60-second interview answer. This can be its own 10-minute sitting.

## Output columns

Your rewrite returns the slow query's columns, in this order:

| # | column | notes |
|---|---|---|
| 1 | lab_id | `labs.lab_id` |
| 2 | patient_id | `labs.patient_id` |
| 3 | site_name | `sites.site_name` of the `sites` row with the same `site_id` |
| 4 | collected_at | `labs.collected_at`; rows sorted by it, newest first |
| 5 | value | `labs.value` (can be NULL) |
| 6 | unit | `labs.unit` |

## Check

```powershell
python tasks.py perf 13
```

Done when `perf` prints `Rewrite returns the same result as the slow query: YES` and the answer file is filled
in. Graded by your explanation and the timing comparison (plus that correctness check), not a hash alone.
`python tasks.py check-sql 13` checks only your rewrite's result, without timing.

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
