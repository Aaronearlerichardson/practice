# 12. "As of": what did we believe before the correction?

**Timebox: 25 min** · Tables: `labs` · Write your answer in `02_sql/solutions/12_as_of_before_correction.sql`

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

A regulatory dataset was cut on **2025-10-01 00:00:00**. Since then, sites have corrected some results. Auditors
want every result at site **S04** whose current value differs from what the cut would have contained.

## Task

For each S04 record (`source_record_id`):
- **as-of version**: the latest version with `loaded_at <= '2025-10-01 00:00:00'` (ties: highest `lab_id`).
- **current version**: the latest version overall (same tie rule).

Return records that have an as-of version, whose current version was loaded **after** the cut, and whose value
**differs**. Treat NULL vs. a number as different, and NULL vs. NULL as the same.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | source_record_id | |
| 2 | test_code | |
| 3 | value_as_of | |
| 4 | current_value | |
| 5 | current_loaded_at | |

## Check

```powershell
python tasks.py check-sql 12
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Two CTEs (as-of and current), each one row per record, joined on `source_record_id`.
2. `DISTINCT ON (source_record_id) ... ORDER BY source_record_id, loaded_at DESC, lab_id DESC` is a compact way to write latest-per-key in Postgres.
3. `a <> b` is NULL when either side is NULL. Look up `IS DISTINCT FROM`.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Iceberg can time-travel (`FOR TIMESTAMP AS OF`). Why might you still keep an append-only version history in the table itself?
- How do you make a dataset cut reproducible years later?

</details>
