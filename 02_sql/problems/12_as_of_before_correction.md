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

**Goal:** return one row per site S04 record whose value changed after the cut at `2025-10-01 00:00:00`: the cut
already held a version of the record, a newer version was loaded after the cut, and the newer `value` differs from
the one the cut held. Each row shows the value at the cut, the current value, and when the current version was
loaded.

1. **Keep site S04.** Use only `labs` rows with `site_id = 'S04'`. A record is one `source_record_id`, and each row
   is one version of it. All versions of a record have the same `test_code`.
2. **Find each record's as-of version (what the cut held).** For each `source_record_id`, look only at its rows
   with `loaded_at <= '2025-10-01 00:00:00'`. A row loaded at exactly `2025-10-01 00:00:00` counts. Of those rows,
   the as-of version is the one with the latest `loaded_at`. When several share it, it is the one with the highest
   `lab_id`. A record with no such row has no as-of version. `value_as_of` is the as-of version's `value`.
3. **Find each record's current version.** For each `source_record_id`, look at all its rows. The current version
   is the one with the latest `loaded_at`. When several share it, it is the one with the highest `lab_id`.
   `current_value` is the current version's `value`, and `current_loaded_at` is its `loaded_at`.
4. **Keep the records that changed after the cut.** Keep a `source_record_id` when all three are true:
   - (a) It has an as-of version (at least one row with `loaded_at <= '2025-10-01 00:00:00'`).
   - (b) `current_loaded_at > '2025-10-01 00:00:00'`.
   - (c) `value_as_of` and `current_value` differ. NULL vs. a number counts as different. NULL vs. NULL counts as
     the same.

   For each kept record, return its `source_record_id`, its `test_code` (the same on every version),
   `value_as_of`, `current_value` and `current_loaded_at`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | source_record_id | one row per record kept in step 4 |
| 2 | test_code | the record's `test_code` (the same on every version) |
| 3 | value_as_of | from step 2: `value` of the as-of version |
| 4 | current_value | from step 3: `value` of the current version |
| 5 | current_loaded_at | from step 3: `loaded_at` of the current version |

## Example

Input `labs` (only the columns this task reads):

```text
+--------+---------+------------------+-----------+--------+---------------------+
| lab_id | site_id | source_record_id | test_code | value  | loaded_at           |
+--------+---------+------------------+-----------+--------+---------------------+
| 1      | S04     | S04-L0000131     | K         | 3.80   | 2025-04-27 18:28:24 |
| 2      | S09     | S09-L0000021     | CREAT     | 95.00  | 2025-07-10 02:16:54 |
| 3      | S04     | S04-L0000010     | GLU       | 5.20   | 2025-07-11 00:14:37 |
| 4      | S04     | S04-L0000131     | K         | 4.10   | 2025-07-11 00:14:37 |
| 5      | S04     | S04-L0000157     | GLU       | 9.30   | 2025-07-11 00:14:37 |
| 6      | S04     | S04-L0000172     | K         | NULL   | 2025-10-01 00:00:00 |
| 7      | S04     | S04-L0000010     | GLU       | 5.50   | 2025-10-29 13:16:13 |
| 8      | S04     | S04-L0000151     | NA        | 138.00 | 2025-10-29 13:16:13 |
| 9      | S09     | S09-L0000021     | CREAT     | 110.00 | 2025-11-09 22:56:15 |
| 10     | S04     | S04-L0000157     | GLU       | 10.10  | 2026-02-15 22:45:03 |
| 11     | S04     | S04-L0000157     | GLU       | 9.30   | 2026-02-15 22:45:03 |
| 12     | S04     | S04-L0000172     | K         | 4.30   | 2026-02-15 22:45:03 |
+--------+---------+------------------+-----------+--------+---------------------+
```

Output:

```text
+------------------+-----------+-------------+---------------+---------------------+
| source_record_id | test_code | value_as_of | current_value | current_loaded_at   |
+------------------+-----------+-------------+---------------+---------------------+
| S04-L0000010     | GLU       | 5.20        | 5.50          | 2025-10-29 13:16:13 |
| S04-L0000172     | K         | NULL        | 4.30          | 2026-02-15 22:45:03 |
+------------------+-----------+-------------+---------------+---------------------+
```

Explanation:

- **Step 1.** lab_id 2 and 9 are dropped: their `site_id` is `'S09'`. Their value did change across the cut (95.00
  to 110.00), but they are not an S04 record.
- **Step 2.** As-of versions: `S04-L0000010` is lab_id 3 (5.20). `S04-L0000131` is lab_id 4 (4.10), loaded later
  than lab_id 1. `S04-L0000157` is lab_id 5 (9.30). `S04-L0000172` is lab_id 6 (NULL): it was loaded at exactly
  `2025-10-01 00:00:00`, and `<=` includes it. `S04-L0000151` has no as-of version: its only row was loaded on
  2025-10-29, after the cut.
- **Step 3.** Current versions: `S04-L0000010` is lab_id 7 (5.50, loaded 2025-10-29 13:16:13). `S04-L0000131` is
  lab_id 4 (4.10, loaded 2025-07-11 00:14:37). `S04-L0000151` is lab_id 8 (138.00). For `S04-L0000157`, lab_id 10
  and 11 share the latest `loaded_at` (2026-02-15 22:45:03), so lab_id 11 (9.30, the higher `lab_id`) is current.
  `S04-L0000172` is lab_id 12 (4.30, loaded 2026-02-15 22:45:03).
- **Step 4.** `S04-L0000010` is kept: 5.20 and 5.50 differ, and its current version was loaded after the cut.
  `S04-L0000172` is kept: NULL vs. 4.30 counts as different. `S04-L0000151` fails (a): it has no as-of version.
  `S04-L0000131` fails (b): its current version, lab_id 4, was loaded before the cut. `S04-L0000157` fails (c): its
  as-of and current values are both 9.30 (lab_id 10's 10.10 lost the tie in step 3).

The real answer has 594 rows.

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
