# 01. Latest HbA1c per patient, keeping ties

**Timebox: 15 min** · Tables: `labs` · Write your answer in `02_sql/solutions/01_latest_hba1c_with_ties.sql`

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

A diabetes study needs each patient's most recent HbA1c. Some patients have two results with the **same**
`collected_at` (repeat draws, or a correction resent by the site). Downstream wants to see all of them so a
person can adjudicate, so don't pick one arbitrarily.

## Task

Use only `labs` rows with `test_code = 'HBA1C'`. Keep every row as loaded, including corrected versions (several
rows with the same `site_id` and `source_record_id`).

For each `patient_id`, find the maximum `collected_at` among those rows. Return every row whose `collected_at`
equals that maximum for its `patient_id`. When several rows share the maximum, return all of them.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | |
| 2 | lab_id | |
| 3 | collected_at | equals the patient's maximum `collected_at` |
| 4 | value | as stored (can be NULL) |

## Check

```powershell
python tasks.py check-sql 01
```

Row order and column names don't matter. Column **order** does. Numbers are compared at 2 decimal places.

<details><summary>Hints (open one at a time)</summary>

1. Which window function keeps ties: `ROW_NUMBER`, `RANK`, or `DENSE_RANK`? Which of those would also work here, and why?
2. A non-window answer: join to `SELECT patient_id, max(collected_at) ... GROUP BY patient_id`.
3. Also try `DISTINCT ON`. Why is it the wrong tool when you must keep ties?

</details>

<details><summary>Follow-ups an interviewer might ask</summary>

- How would you make this fast for one patient at a time (dashboard)? For all patients (batch)?
- If ties were not allowed downstream, what deterministic tie-breaker would you choose and why?

</details>
