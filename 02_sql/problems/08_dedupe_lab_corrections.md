# 08. Deduplicate corrected lab records

**Timebox: 20 min** · Tables: `labs` · Write your answer in `02_sql/solutions/08_dedupe_lab_corrections.sql`

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

`labs` is append-only. When a site corrects a result, it resends the same `source_record_id` in a later batch,
usually with a different value. Silver-layer tables must hold one row per record: the latest version.

## Task

Use only `labs` rows with `site_id = 'S07'`.

Return one row per `source_record_id`. Of that `source_record_id`'s rows, keep the one with the latest
`loaded_at`. When several of its rows share that latest `loaded_at` (two versions in the same batch), keep the one
with the highest `lab_id` (the later line in the file).

## Output columns

| # | column | notes |
|---|---|---|
| 1 | source_record_id | |
| 2 | lab_id | of the kept row |
| 3 | value | of the kept row (can be NULL) |
| 4 | loaded_at | of the kept row |
| 5 | n_versions | number of rows with this `source_record_id`; 1 for a record never corrected |

## Check

```powershell
python tasks.py check-sql 08
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. `row_number() OVER (PARTITION BY site_id, source_record_id ORDER BY loaded_at DESC, lab_id DESC)`.
2. `count(*) OVER (PARTITION BY ...)` in the same SELECT gives n_versions without a second pass.
3. Try `DISTINCT ON` too, and compare the plans.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- How would you express this as an incremental dbt model (merge on the key)?
- What if the site resent an identical value? Is that a 'conflict'? How would you report true conflicts only?

</details>
