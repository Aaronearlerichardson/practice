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

**Goal:** return one row per `test_code` with five statistics of `value`: the row count, the 10th percentile, the
median, the 90th percentile and the mean. Count only the latest version of each record, and only results reported
in the test's canonical unit.

1. **Keep the latest version of each record.** A record is one (`site_id`, `source_record_id`) pair, and each
   `labs` row is one version of it. For each pair, keep the row with the latest `loaded_at`. When several rows share
   that `loaded_at`, keep the one with the highest `lab_id`. Run this on all `labs` rows, before any other filter.
2. **Drop NULL values and other units.** Of the step 1 rows, keep those where `value IS NOT NULL` and
   `lower(unit) = lower(canonical unit)` for the row's `test_code` (table below). A record whose latest version is
   dropped here is gone: an older version does not replace it. Rows in another unit (GLU in `mmol/L`, CREAT in
   `umol/L`, HGB in `g/L`) are dropped, not converted.
3. **Compute the statistics.** Group the step 2 rows by `test_code`. For each group compute:
   - `n`: the number of rows
   - `p10`: `percentile_disc(0.10)` of `value`
   - `median`: `percentile_cont(0.50)` of `value`
   - `p90`: `percentile_disc(0.90)` of `value`
   - `mean`: the average of `value`, rounded to 2 decimals

| test_code | GLU | CREAT | HGB | K | NA | ALT | HBA1C | PLT |
|---|---|---|---|---|---|---|---|---|
| canonical unit | mg/dL | mg/dL | g/dL | mmol/L | mmol/L | U/L | % | 10*3/uL |

## Output columns

| # | column | notes |
|---|---|---|
| 1 | test_code | 8 rows, one per `test_code` |
| 2 | n | number of step 2 rows for the `test_code` |
| 3 | p10 | `percentile_disc(0.10)` of `value` |
| 4 | median | `percentile_cont(0.50)` of `value` |
| 5 | p90 | `percentile_disc(0.90)` of `value` |
| 6 | mean | average of `value`, rounded to 2 decimals |

## Example

Input `labs` (only the columns this task reads):

```text
+--------+---------+------------------+-----------+--------+--------+---------------------+
| lab_id | site_id | source_record_id | test_code | value  | unit   | loaded_at           |
+--------+---------+------------------+-----------+--------+--------+---------------------+
| 1      | S01     | S01-L0000001     | GLU       | 300.00 | mg/dL  | 2025-04-01 00:00:00 |
| 2      | S01     | S01-L0000002     | GLU       | 110.00 | mg/dL  | 2025-04-01 00:00:00 |
| 3      | S02     | S02-L0000001     | GLU       | 120.00 | mg/dl  | 2025-04-01 00:00:00 |
| 4      | S02     | S02-L0000002     | GLU       | 6.10   | mmol/L | 2025-04-01 00:00:00 |
| 5      | S02     | S02-L0000003     | GLU       | 105.00 | mg/dL  | 2025-04-01 00:00:00 |
| 6      | S03     | S03-L0000001     | GLU       | 250.00 | mg/dL  | 2025-04-01 00:00:00 |
| 7      | S03     | S03-L0000002     | K         | 4.20   | mmol/L | 2025-04-01 00:00:00 |
| 8      | S03     | S03-L0000002     | K         | 4.00   | mmol/L | 2025-04-01 00:00:00 |
| 9      | S03     | S03-L0000003     | K         | 5.00   | mmol/L | 2025-04-01 00:00:00 |
| 10     | S01     | S01-L0000001     | GLU       | 95.00  | mg/dL  | 2025-07-01 00:00:00 |
| 11     | S02     | S02-L0000003     | GLU       | NULL   | mg/dL  | 2025-07-01 00:00:00 |
+--------+---------+------------------+-----------+--------+--------+---------------------+
```

Output:

```text
+-----------+---+-------+--------+--------+--------+
| test_code | n | p10   | median | p90    | mean   |
+-----------+---+-------+--------+--------+--------+
| GLU       | 4 | 95.00 | 115.00 | 250.00 | 143.75 |
| K         | 2 | 4.00  | 4.50   | 5.00   | 4.50   |
+-----------+---+-------+--------+--------+--------+
```

Explanation:

- **Step 1.** (`S01`, `S01-L0000001`) has two versions: lab_id 10 has the later `loaded_at`, so it is kept and
  lab_id 1 is dropped. (`S03`, `S03-L0000002`) has two versions with the same `loaded_at`: lab_id 8 has the
  higher `lab_id`, so it is kept. (`S02`, `S02-L0000003`) keeps lab_id 11, whose `value` is NULL.
- **Step 2.** lab_id 11 is dropped (NULL `value`), and lab_id 5 does not come back, because step 1 already dropped
  it. lab_id 4 is dropped: `mmol/L` is not GLU's canonical unit. lab_id 3 stays: `lower('mg/dl') = lower('mg/dL')`.
- **Step 3.** GLU keeps 95, 110, 120 and 250. `p10` = 95 and `p90` = 250 (`percentile_disc` always returns one of
  the values). `median` = (110 + 120) / 2 = 115 (`percentile_cont` interpolates between the middle two).
  `mean` = 575 / 4 = 143.75. K keeps 4.00 and 5.00.

The real answer has 8 rows, one per `test_code`.

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
