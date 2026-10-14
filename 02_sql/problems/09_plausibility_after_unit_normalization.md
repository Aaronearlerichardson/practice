# 09. Plausibility violations after unit normalization

**Timebox: 25 min** · Tables: `labs` · Write your answer in `02_sql/solutions/09_plausibility_after_unit_normalization.sql`

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

Medical plausibility checks only make sense in one unit system. Some sites report SI units, and one site
lowercases units (`mg/dl`).

## Task

**Goal:** return one row per lab result whose value is implausible: after `value` is converted to the test's
canonical unit, it falls outside the test's plausible range. Check only the latest version of each record, at all
sites, and skip NULL values. Each row says whether the value is below or above the range.

1. **Keep the latest version of each record.** A record is one (`site_id`, `source_record_id`) pair, and each
   `labs` row is one version of it. For each pair, keep the row with the latest `loaded_at`. When several rows share
   that `loaded_at`, keep the one with the highest `lab_id`. Run this on all `labs` rows from all sites, before any
   other filter.
2. **Drop NULL values.** Of the step 1 rows, drop those where `value IS NULL`. A record whose latest version is
   dropped here is gone: an older version does not replace it.
3. **Convert to the canonical unit.** The canonical unit is the one standard unit each test is checked in (table
   below). For each step 2 row, compute `normalized_value`. Compare `unit` case-insensitively (`lower(unit)`), so
   `mg/dl` matches `mg/dL`. When `unit` matches the canonical unit, `normalized_value = value`. When it matches the
   other unit, `normalized_value` is the formula applied to `value` (GLU in `mmol/L`: `value * 18`). Every row's
   `unit` is one of the two.
4. **Keep the values outside the plausible range.** Keep the step 3 rows whose `normalized_value` is below the low
   end or above the high end of the test's plausible range (table below). The range includes both ends: a
   `normalized_value` equal to the low end or the high end is plausible, so that row is not returned. Compare the
   **unrounded** `normalized_value`.
5. **Label the reason, then round.** For each step 4 row, set `reason` to `'below_range'` if `normalized_value` is
   below the range's low end, or `'above_range'` if it is above the high end. Then round `normalized_value` to 2
   decimals for the output (only now, after the step 4 comparison).

| test_code | canonical unit | plausible range | other unit | formula |
|---|---|---|---|---|
| GLU | mg/dL | 20 to 1000 | mmol/L | `value * 18` |
| CREAT | mg/dL | 0.1 to 20 | umol/L | `value / 88.4` |
| HGB | g/dL | 3 to 25 | g/L | `value / 10` |
| K | mmol/L | 1.5 to 9 | none | |
| NA | mmol/L | 100 to 180 | none | |
| ALT | U/L | 1 to 5000 | none | |
| HBA1C | % | 3 to 20 | none | |
| PLT | 10*3/uL | 1 to 2000 | none | |

## Output columns

| # | column | notes |
|---|---|---|
| 1 | lab_id | of the kept row (the record's latest version, from step 1) |
| 2 | site_id | as stored |
| 3 | test_code | as stored |
| 4 | value | as stored, not converted |
| 5 | unit | as stored, not lowercased |
| 6 | normalized_value | from step 3, rounded to 2 decimals in step 5 |
| 7 | reason | from step 5: `'below_range'` or `'above_range'` |

## Example

Input `labs` (only the columns this task reads):

```text
+--------+---------+------------------+-----------+---------+--------+---------------------+
| lab_id | site_id | source_record_id | test_code | value   | unit   | loaded_at           |
+--------+---------+------------------+-----------+---------+--------+---------------------+
| 1      | S04     | S04-L0000001     | GLU       | 0.90    | mmol/L | 2025-04-27 18:28:24 |
| 2      | S04     | S04-L0000002     | GLU       | 5.50    | mmol/L | 2025-04-27 18:28:24 |
| 3      | S04     | S04-L0000003     | CREAT     | 2000.00 | umol/L | 2025-04-27 18:28:24 |
| 4      | S04     | S04-L0000004     | CREAT     | 8.80    | umol/L | 2025-04-27 18:28:24 |
| 5      | S02     | S02-L0000001     | HGB       | NULL    | g/dL   | 2025-05-08 09:21:12 |
| 6      | S06     | S06-L0000001     | GLU       | 1200.00 | mg/dl  | 2025-05-12 17:40:23 |
| 7      | S06     | S06-L0000002     | GLU       | 85.00   | mg/dl  | 2025-05-12 17:40:23 |
| 8      | S06     | S06-L0000002     | GLU       | 15.00   | mg/dl  | 2025-05-12 17:40:23 |
| 9      | S01     | S01-L0000001     | GLU       | 1500.00 | mg/dL  | 2025-05-12 19:08:34 |
| 10     | S01     | S01-L0000002     | K         | 9.00    | mmol/L | 2025-05-12 19:08:34 |
| 11     | S01     | S01-L0000001     | GLU       | 150.00  | mg/dL  | 2025-07-27 20:15:46 |
+--------+---------+------------------+-----------+---------+--------+---------------------+
```

Output:

```text
+--------+---------+-----------+---------+--------+------------------+-------------+
| lab_id | site_id | test_code | value   | unit   | normalized_value | reason      |
+--------+---------+-----------+---------+--------+------------------+-------------+
| 1      | S04     | GLU       | 0.90    | mmol/L | 16.20            | below_range |
| 3      | S04     | CREAT     | 2000.00 | umol/L | 22.62            | above_range |
| 4      | S04     | CREAT     | 8.80    | umol/L | 0.10             | below_range |
| 6      | S06     | GLU       | 1200.00 | mg/dl  | 1200.00          | above_range |
| 8      | S06     | GLU       | 15.00   | mg/dl  | 15.00            | below_range |
+--------+---------+-----------+---------+--------+------------------+-------------+
```

Explanation:

- **Step 1.** (`S01`, `S01-L0000001`) has two versions: lab_id 11 has the later `loaded_at`, so it is kept and
  lab_id 9 is dropped. lab_id 9's 1500.00 would have been above GLU's range, but it is not the latest version, so
  it is never checked. (`S06`, `S06-L0000002`) has two versions with the same `loaded_at`: lab_id 8 has the higher
  `lab_id`, so it is kept and lab_id 7 is dropped. Every other record has one version, which is kept.
- **Step 2.** lab_id 5 is dropped: its `value` is NULL.
- **Step 3.** The `S04` rows are in the other unit, so the formula applies: lab_id 1 is 0.90 * 18 = 16.2, lab_id 2
  is 5.50 * 18 = 99, lab_id 3 is 2000.00 / 88.4 = 22.624434... and lab_id 4 is 8.80 / 88.4 = 0.099547... (both
  unrounded). lab_id 6 and 8 have `unit = 'mg/dl'`, and `lower('mg/dl') = lower('mg/dL')`, so they are already
  in GLU's canonical unit and `normalized_value = value`. lab_id 10 and 11 are also in their canonical units.
- **Step 4.** Below the low end: lab_id 1 (16.2 < 20), lab_id 4 (0.099547... < 0.1) and lab_id 8 (15 < 20). Above
  the high end: lab_id 3 (22.624434... > 20) and lab_id 6 (1200 > 1000). lab_id 10 is K = 9.00, exactly K's high
  end, and the range includes both ends, so it is not returned. lab_id 2 (99) and lab_id 11 (150) are inside GLU's
  20 to 1000.
- **Step 5.** lab_id 1, 4 and 8 get `'below_range'`; lab_id 3 and 6 get `'above_range'`. Rounding gives 16.20,
  22.62, 0.10, 1200.00 and 15.00. lab_id 4 shows 0.10, which is CREAT's low end, but step 4 compared the unrounded
  0.099547..., which is below 0.1, so it is still returned.

The real answer has 4976 rows.

## Check

```powershell
python tasks.py check-sql 09
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Build it in CTEs: latest, then normalized, then a `ranges(test_code, low, high) AS (VALUES ...)` CTE, then join.
2. A `CASE` on `(test_code, lower(unit))` does the conversion.
3. Sanity check: count violations per site and reason. Does any site stand out? Why?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- Where would this rule live in the stack: a dbt test, a Great Expectations suite, or a silver-model column? Trade-offs?
- Hard-coding conversions in SQL vs. a seed/reference table: which, and why?

</details>
