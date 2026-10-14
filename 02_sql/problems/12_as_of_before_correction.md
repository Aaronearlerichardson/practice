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

Use only `labs` rows with `site_id = 'S04'`. A record is one `source_record_id`, and each row is one version of it.
All versions of a record have the same `test_code`.

For each `source_record_id`, find two versions:
- **as-of version**: among its rows with `loaded_at <= '2025-10-01 00:00:00'`, the one with the latest
  `loaded_at`. When several share it, the one with the highest `lab_id`.
- **current version**: among all its rows, the one with the latest `loaded_at`. When several share it, the one
  with the highest `lab_id`.

Return the `source_record_id` when all three are true:
1. It has an as-of version (at least one row with `loaded_at <= '2025-10-01 00:00:00'`).
2. Its current version has `loaded_at > '2025-10-01 00:00:00'`.
3. The as-of version's `value` and the current version's `value` differ. NULL vs. a number counts as different.
   NULL vs. NULL counts as the same.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | source_record_id | |
| 2 | test_code | |
| 3 | value_as_of | `value` of the as-of version |
| 4 | current_value | `value` of the current version |
| 5 | current_loaded_at | `loaded_at` of the current version |

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
