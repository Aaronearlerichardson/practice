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

**Goal:** return one row per `source_record_id` at site `S07`: the latest version of that record (its `lab_id`,
`value` and `loaded_at`) and how many versions of it were loaded. This is the silver-layer table: one row per
record.

1. **Keep only site S07.** Use only `labs` rows with `site_id = 'S07'`. Every later step works on these rows.
2. **Count the versions of each record.** A record is one `source_record_id`, and each step 1 row is one version of
   it. For each `source_record_id`, `n_versions` is the number of step 1 rows with that `source_record_id`. It is 1
   for a record that was never corrected.
3. **Keep the latest version.** For each `source_record_id`, of its step 1 rows keep the one with the latest
   `loaded_at`. When several of its rows share that latest `loaded_at` (two versions in the same batch), keep the
   one with the highest `lab_id` (the later line in the file).
4. **Return the kept row.** For each `source_record_id`, return the step 3 row's `lab_id`, `value` and
   `loaded_at`, with `n_versions` from step 2. Keep the row even when its `value` is NULL.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | source_record_id | one row per `source_record_id` at `S07` |
| 2 | lab_id | of the step 3 row |
| 3 | value | of the step 3 row (can be NULL) |
| 4 | loaded_at | of the step 3 row |
| 5 | n_versions | from step 2: number of `S07` rows with this `source_record_id`; 1 for a record never corrected |

## Example

Input `labs` (only the columns this task reads):

```text
+--------+---------+------------------+--------+---------------------+
| lab_id | site_id | source_record_id | value  | loaded_at           |
+--------+---------+------------------+--------+---------------------+
| 32     | S07     | S07-L0000113     | 6.40   | 2023-04-10 08:52:10 |
| 33     | S07     | S07-L0000113     | 5.70   | 2023-04-10 08:52:10 |
| 95     | S07     | S07-L0000511     | 4.70   | 2023-04-10 08:52:10 |
| 120    | S07     | S07-L0000520     | 98.00  | 2023-04-10 08:52:10 |
| 131    | S07     | S07-L0000527     | 13.40  | 2023-04-10 08:52:10 |
| 140    | S03     | S03-L0000034     | 140.00 | 2023-04-12 10:15:42 |
| 146111 | S07     | S07-L0000511     | 6.10   | 2023-08-07 12:09:09 |
| 182230 | S07     | S07-L0000527     | NULL   | 2023-10-25 08:46:20 |
| 236225 | S07     | S07-L0000511     | 6.00   | 2024-01-07 22:30:22 |
+--------+---------+------------------+--------+---------------------+
```

Output:

```text
+------------------+--------+-------+---------------------+------------+
| source_record_id | lab_id | value | loaded_at           | n_versions |
+------------------+--------+-------+---------------------+------------+
| S07-L0000113     | 33     | 5.70  | 2023-04-10 08:52:10 | 2          |
| S07-L0000511     | 236225 | 6.00  | 2024-01-07 22:30:22 | 3          |
| S07-L0000520     | 120    | 98.00 | 2023-04-10 08:52:10 | 1          |
| S07-L0000527     | 182230 | NULL  | 2023-10-25 08:46:20 | 2          |
+------------------+--------+-------+---------------------+------------+
```

Explanation:

- **Step 1.** lab_id 140 is at site `S03`, so it is dropped. The other 8 rows are at `S07`.
- **Step 2.** `S07-L0000511` has 3 rows (lab_id 95, 146111 and 236225), so `n_versions` = 3. `S07-L0000113`
  (lab_id 32 and 33) and `S07-L0000527` (lab_id 131 and 182230) have 2 each. `S07-L0000520` has only lab_id 120:
  it was never corrected, so `n_versions` = 1.
- **Step 3.** `S07-L0000511` keeps lab_id 236225, whose `loaded_at` (2024-01-07 22:30:22) is the latest of its
  three. Both rows of `S07-L0000113` have `loaded_at` 2023-04-10 08:52:10, so the higher `lab_id`, 33, is kept.
  `S07-L0000527` keeps lab_id 182230, the later version. `S07-L0000520` keeps its only row, lab_id 120.
- **Step 4.** The kept row for `S07-L0000527` has a NULL `value`, so its output row shows NULL.

The real answer has 135125 rows, one per `source_record_id` at `S07`.

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
