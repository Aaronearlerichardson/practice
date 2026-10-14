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

1. **Latest version of each record, all sites.** A record is one (`site_id`, `source_record_id`) pair, and each
   `labs` row is one version of it. For each pair, keep the row with the latest `loaded_at`. When several rows share
   that `loaded_at`, keep the one with the highest `lab_id`.
2. Drop rows where `value IS NULL`.
3. **Normalize** `value` into `normalized_value` with the table below. The canonical unit is the one standard unit
   each test is checked in. Compare `unit` case-insensitively (`lower(unit)`), so `mg/dl` matches `mg/dL`. When
   `unit` matches the canonical unit, `normalized_value = value`. When it matches the other unit, apply the
   formula. Every row's `unit` is one of the two.
4. Return the rows whose `normalized_value` is outside the plausible range. The range includes both ends. Compare
   the **unrounded** `normalized_value`; round it only in the output.

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
| 1 | lab_id | of the kept row |
| 2 | site_id | |
| 3 | test_code | |
| 4 | value | as stored |
| 5 | unit | as stored |
| 6 | normalized_value | rounded to 2 decimals |
| 7 | reason | `'below_range'` if `normalized_value` is below the range's low end, `'above_range'` if above its high end |

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
