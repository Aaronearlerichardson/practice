# 10. Pivot test codes into columns

**Timebox: 20 min** · Tables: `labs` · Write your answer in `02_sql/solutions/10_pivot_latest_labs.sql`

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

A data scientist wants one row per patient with each patient's latest 2025 value for a few tests, as columns.

## Task

1. Use only `labs` rows with `site_id = 'S03'`.
2. **Latest version of each record.** For each `source_record_id`, keep the row with the latest `loaded_at`. When
   several rows share that `loaded_at`, keep the one with the highest `lab_id`.
3. Of those, keep rows with `test_code` in (`'GLU'`, `'HBA1C'`, `'CREAT'`, `'K'`) and
   `collected_at >= '2025-01-01'` and `collected_at < '2026-01-01'`.
4. For each (`patient_id`, `test_code`), take the row with the latest `collected_at`. When several share it, take
   the one with the highest `lab_id`.
5. Pivot: one output row per `patient_id` that has at least one row after step 3. Each test's column holds the
   `value` of that patient's step 4 row for the test. A test with no row for the patient is NULL.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | |
| 2 | glu | `value` of the step 4 row with `test_code = 'GLU'` |
| 3 | hba1c | `value` of the step 4 row with `test_code = 'HBA1C'` |
| 4 | creat | `value` of the step 4 row with `test_code = 'CREAT'` |
| 5 | k | `value` of the step 4 row with `test_code = 'K'` |

## Check

```powershell
python tasks.py check-sql 10
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Rank within `(patient_id, test_code)`, keep rank 1, then pivot.
2. Pivot with `max(value) FILTER (WHERE test_code = 'GLU') AS glu`, and so on, grouped by patient.
3. Postgres has `crosstab()` in the `tablefunc` extension. Why is the FILTER form usually preferred?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- What if the list of tests isn't known in advance?
- Wide vs. long tables for analytics: when do you pivot, and where (SQL, dbt, pandas)?

</details>
