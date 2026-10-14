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

1. Group all `labs` rows by `site_id` and `quarter_start = date_trunc('quarter', collected_at)::date`.
2. `n_records` is the number of distinct `source_record_id` values in the group. A corrected record has several rows
   with the same `source_record_id` (and the same `collected_at`), so it counts once.
3. `prev_n_records` is the `n_records` of the same `site_id` for the quarter before
   (`quarter_start - interval '3 months'`). No site skips a quarter. It is NULL for each site's first quarter.
4. `pct_change` is `100 * (n_records - prev_n_records) / prev_n_records`, rounded to 2 decimals. It is NULL when
   `prev_n_records` is NULL.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | site_id | |
| 2 | quarter_start | `date` |
| 3 | n_records | distinct `source_record_id` values in the group |
| 4 | prev_n_records | NULL for a site's first quarter |
| 5 | pct_change | rounded to 2 decimals; NULL when `prev_n_records` is NULL |

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
