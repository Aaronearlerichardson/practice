# 03. Quarter-over-quarter lab volume with LAG

**Timebox: 15 min** · Tables: `labs` · Write your answer in `02_sql/solutions/03_qoq_lab_volume_lag.sql`

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

Before accepting a site's quarterly batch, the team compares its volume with the previous quarter. A sudden drop
often means a truncated extract.

## Task

**Goal:** return one row per (`site_id`, quarter of `collected_at`) with the number of distinct records the site has
in that quarter, the same number for the site's previous quarter, and the percent change between the two. Use all
`labs` rows; a corrected record counts once.

1. **Find each row's quarter.** For every `labs` row (no filters; corrected versions included), compute
   `quarter_start = date_trunc('quarter', collected_at)::date`: the first day of the calendar quarter that
   `collected_at` falls in (January 1, April 1, July 1 or October 1).
2. **Count distinct records per site and quarter.** Group the step 1 rows by (`site_id`, `quarter_start`).
   `n_records` is the number of distinct `source_record_id` values in the group. A corrected record has several rows
   with the same `source_record_id` (and the same `collected_at`), so it counts once.
3. **Look up the previous quarter.** `prev_n_records` is the `n_records` of the same `site_id` for the quarter before
   (`quarter_start - interval '3 months'`). No site skips a quarter. It is NULL for each site's first quarter (the
   site's earliest `quarter_start`), because the site has no row for the quarter before.
4. **Compute the percent change.** `pct_change` is `100 * (n_records - prev_n_records) / prev_n_records`, rounded to
   2 decimals. It is NULL when `prev_n_records` is NULL. Return `site_id`, `quarter_start`, `n_records`,
   `prev_n_records` and `pct_change`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | from step 2 |
| 2 | quarter_start | `date`, from step 1 |
| 3 | n_records | from step 2: distinct `source_record_id` values in the group |
| 4 | prev_n_records | from step 3; NULL for a site's first quarter |
| 5 | pct_change | from step 4; rounded to 2 decimals; NULL when `prev_n_records` is NULL |

## Example

Input `labs` (only the columns this task reads, plus `lab_id` and `loaded_at` to show which row is a correction):

```text
+--------+---------+------------------+---------------------+---------------------+
| lab_id | site_id | source_record_id | collected_at        | loaded_at           |
+--------+---------+------------------+---------------------+---------------------+
| 1      | S03     | S03-L0000071     | 2025-02-10 13:20:41 | 2025-04-09 08:52:10 |
| 2      | S03     | S03-L0000077     | 2025-03-31 23:50:12 | 2025-04-09 08:52:10 |
| 3      | S03     | S03-L0000085     | 2025-01-02 07:41:47 | 2025-04-09 08:52:10 |
| 4      | S05     | S05-L0000040     | 2025-05-06 10:12:33 | 2025-07-08 09:15:44 |
| 5      | S03     | S03-L0000089     | 2025-04-01 00:05:52 | 2025-07-09 08:52:10 |
| 6      | S03     | S03-L0000094     | 2025-05-14 16:09:05 | 2025-07-09 08:52:10 |
| 7      | S03     | S03-L0000071     | 2025-02-10 13:20:41 | 2025-07-09 08:52:10 |
| 8      | S05     | S05-L0000052     | 2025-08-12 14:47:20 | 2025-10-07 09:15:44 |
| 9      | S05     | S05-L0000058     | 2025-09-02 08:26:39 | 2025-10-07 09:15:44 |
| 10     | S03     | S03-L0000101     | 2025-07-03 09:31:27 | 2025-10-08 08:52:10 |
| 11     | S03     | S03-L0000106     | 2025-08-19 11:02:58 | 2025-10-08 08:52:10 |
| 12     | S03     | S03-L0000112     | 2025-09-30 22:10:16 | 2025-10-08 08:52:10 |
+--------+---------+------------------+---------------------+---------------------+
```

Output:

```text
+---------+---------------+-----------+----------------+------------+
| site_id | quarter_start | n_records | prev_n_records | pct_change |
+---------+---------------+-----------+----------------+------------+
| S03     | 2025-01-01    | 3         | NULL           | NULL       |
| S03     | 2025-04-01    | 2         | 3              | -33.33     |
| S03     | 2025-07-01    | 3         | 2              | 50.00      |
| S05     | 2025-04-01    | 1         | NULL           | NULL       |
| S05     | 2025-07-01    | 2         | 1              | 100.00     |
+---------+---------------+-----------+----------------+------------+
```

Explanation:

- **Step 1.** lab_ids 1, 2, 3 and 7 fall in the quarter starting 2025-01-01. lab_id 2 (2025-03-31 23:50:12) is still
  in that quarter, and lab_id 5 (2025-04-01 00:05:52) is in the quarter starting 2025-04-01. lab_id 7 was loaded in
  July, but its `collected_at` is in February, and `collected_at` decides the quarter.
- **Step 2.** S03's 2025-01-01 quarter has 4 rows but 3 distinct `source_record_id` values: lab_ids 1 and 7 are the
  same record (`S03-L0000071`, corrected and resent), so it counts once. S03 has 2 records in the 2025-04-01
  quarter (lab_ids 5, 6) and 3 in the 2025-07-01 quarter (lab_ids 10, 11, 12). S05 has 1 in 2025-04-01 (lab_id 4)
  and 2 in 2025-07-01 (lab_ids 8, 9).
- **Step 3.** S03's first quarter is 2025-01-01, so its `prev_n_records` is NULL. S03's 2025-04-01 quarter looks
  back to 2025-01-01 (3), and its 2025-07-01 quarter looks back to 2025-04-01 (2). S05's first quarter is
  2025-04-01, so it is NULL there, even though S03 has a 2025-01-01 row: only the same `site_id` counts.
- **Step 4.** S03 2025-04-01: 100 * (2 - 3) / 3 = -33.333..., rounded to -33.33. S03 2025-07-01:
  100 * (3 - 2) / 2 = 50.00. S05 2025-07-01: 100 * (2 - 1) / 1 = 100.00. Both first quarters stay NULL.

The example covers three quarters to stay short. The real data covers more quarters (2023 to mid-2026), and the
real answer has 167 rows, one per (`site_id`, `quarter_start`) that has `labs` rows.

## Check

```powershell
python tasks.py check-sql 03
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. `count(DISTINCT source_record_id)`: why not `count(*)`?
2. Aggregate first in a CTE, then apply `LAG` over the aggregated rows.
3. Watch integer division: `100.0 * ...`.

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Every site has a row for every quarter here. What would go wrong with LAG if a quarter were missing entirely, and how would you fix it?
- How would you turn this into an automated volume check (thresholds, seasonality)?

</details>
