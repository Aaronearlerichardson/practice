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

Using the latest version of each record (all sites), keep only rows whose unit equals the test's canonical unit,
**case-insensitively**, with a non-NULL value.

**Latest version** (problem 08's rule): per record, keep the version with the latest `loaded_at`. If two versions share a `loaded_at`, keep the higher `lab_id`.

**Canonical units:** the one standard unit each test is reported in. Sites send some tests in other units (for example GLU in `mmol/L` instead of `mg/dL`); this problem drops those rows rather than converting them.

| test_code | GLU | CREAT | HGB | K | NA | ALT | HBA1C | PLT |
|---|---|---|---|---|---|---|---|---|
| unit | mg/dL | mg/dL | g/dL | mmol/L | mmol/L | U/L | % | 10*3/uL |

Per test, return:

## Output columns

| # | column | notes |
|---|---|---|
| 1 | test_code | 8 rows |
| 2 | n | rows used |
| 3 | p10 | `percentile_disc(0.10)` |
| 4 | median | `percentile_cont(0.50)` |
| 5 | p90 | `percentile_disc(0.90)` |
| 6 | mean | rounded to 2 decimals |

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
- Mean vs. median for lab values: why might they disagree here? (Look at problem 09's violations.)
- How would you compute an approximate median over billions of rows?

</details>
