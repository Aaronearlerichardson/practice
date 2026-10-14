# 11. Median and percentiles per test

**Timebox: 20 min** · Tables: `labs` · Write your answer in `02_sql/solutions/11_lab_percentiles.sql`

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

For a reference-range sanity check, compute distribution statistics per test.

## Task

1. **Latest version of each record, all sites.** A record is one (`site_id`, `source_record_id`) pair, and each
   `labs` row is one version of it. For each pair, keep the row with the latest `loaded_at`. When several rows share
   that `loaded_at`, keep the one with the highest `lab_id`.
2. Keep rows where `value IS NOT NULL` and `lower(unit)` equals `lower(canonical unit)` for the row's
   `test_code`, from the table below. The canonical unit is the one standard unit each test is reported in. Rows
   in another unit (GLU in `mmol/L`, CREAT in `umol/L`, HGB in `g/L`) are dropped, not converted.
3. Group the kept rows by `test_code`.

| test_code | GLU | CREAT | HGB | K | NA | ALT | HBA1C | PLT |
|---|---|---|---|---|---|---|---|---|
| canonical unit | mg/dL | mg/dL | g/dL | mmol/L | mmol/L | U/L | % | 10*3/uL |

## Output columns

| # | column | notes |
|---|---|---|
| 1 | test_code | 8 rows |
| 2 | n | number of kept rows for the `test_code` |
| 3 | p10 | `percentile_disc(0.10)` of `value` |
| 4 | median | `percentile_cont(0.50)` of `value` |
| 5 | p90 | `percentile_disc(0.90)` of `value` |
| 6 | mean | average of `value`, rounded to 2 decimals |

## Check

```powershell
python tasks.py check-sql 11
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. `percentile_cont(0.5) WITHIN GROUP (ORDER BY value)` is an ordered-set aggregate: it goes in the SELECT with GROUP BY.
2. A canon `(test_code, unit)` VALUES list joined on `lower(unit)` is cleaner than a long CASE.
3. Check `n` against a version without the unit filter. How many rows does the unit filter drop, and from which site?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- percentile_cont vs. percentile_disc: what's the difference, and when does it matter?
- Mean vs. median for lab values: why might they disagree here? (Some values are far outside the plausible range for their test.)
- How would you compute an approximate median over billions of rows?

</details>
