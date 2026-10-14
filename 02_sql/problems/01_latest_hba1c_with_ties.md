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

**Goal:** return each patient's most recent HbA1c result: one row per `labs` row with `test_code = 'HBA1C'` whose
`collected_at` is the latest for its `patient_id`, with its `patient_id`, `lab_id`, `collected_at` and `value`. When
several rows share a patient's latest `collected_at`, return all of them.

1. **Keep only HbA1c rows.** From `labs`, keep the rows with `test_code = 'HBA1C'`. Keep every row as loaded,
   including corrected versions (several rows with the same `site_id` and `source_record_id`) and rows whose `value`
   is NULL. Don't remove duplicates.
2. **Find each patient's latest `collected_at`.** For each `patient_id`, take the maximum `collected_at` among the
   step 1 rows. This is the patient's latest `collected_at`. It is computed over all of the patient's step 1 rows,
   whatever their `site_id`.
3. **Return every row at that time.** Keep each step 1 row whose `collected_at` equals its patient's latest
   `collected_at` from step 2. When several rows share it, keep all of them; don't pick one. Return the row's
   `patient_id`, `lab_id`, `collected_at` and `value`.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | from the step 3 row; a patient appears once per tied row |
| 2 | lab_id | from the step 3 row |
| 3 | collected_at | from the step 3 row; equals the patient's latest `collected_at` from step 2 |
| 4 | value | from the step 3 row, as stored (can be NULL) |

## Example

Input `labs` (only the columns this task reads, plus `source_record_id` to show which rows are corrections):

```text
+--------+------------+------------------+-----------+--------+---------------------+
| lab_id | patient_id | source_record_id | test_code | value  | collected_at        |
+--------+------------+------------------+-----------+--------+---------------------+
| 1      | 100047     | S07-L0000054     | HBA1C     | 7.40   | 2025-03-25 17:47:20 |
| 2      | 100047     | S07-L0000065     | HBA1C     | 6.30   | 2025-02-02 09:45:26 |
| 3      | 100047     | S07-L0000071     | GLU       | 182.00 | 2025-05-10 08:15:00 |
| 4      | 100066     | S07-L0000113     | HBA1C     | 6.40   | 2025-03-01 14:22:48 |
| 5      | 100066     | S07-L0000128     | HBA1C     | 7.00   | 2025-01-03 07:06:39 |
| 6      | 100144     | S02-L0000484     | HBA1C     | 5.00   | 2025-02-27 12:54:45 |
| 7      | 100144     | S02-L0000485     | HBA1C     | NULL   | 2025-02-27 12:54:45 |
| 8      | 100144     | S02-L0000501     | HBA1C     | 6.60   | 2025-01-10 08:21:09 |
| 9      | 100066     | S07-L0000113     | HBA1C     | 5.70   | 2025-03-01 14:22:48 |
+--------+------------+------------------+-----------+--------+---------------------+
```

Output:

```text
+------------+--------+---------------------+-------+
| patient_id | lab_id | collected_at        | value |
+------------+--------+---------------------+-------+
| 100047     | 1      | 2025-03-25 17:47:20 | 7.40  |
| 100066     | 4      | 2025-03-01 14:22:48 | 6.40  |
| 100066     | 9      | 2025-03-01 14:22:48 | 5.70  |
| 100144     | 6      | 2025-02-27 12:54:45 | 5.00  |
| 100144     | 7      | 2025-02-27 12:54:45 | NULL  |
+------------+--------+---------------------+-------+
```

Explanation:

- **Step 1.** lab_id 3 is dropped: its `test_code` is `GLU`. The other 8 rows stay, including lab_id 9 (a
  correction: same `source_record_id` as lab_id 4, loaded later) and lab_id 7 (NULL `value`).
- **Step 2.** Patient 100047's latest `collected_at` is 2025-03-25 17:47:20 (lab_id 1). The GLU row is later
  (2025-05-10), but step 1 already dropped it. Patient 100066's latest is 2025-03-01 14:22:48 (lab_ids 4 and 9).
  Patient 100144's latest is 2025-02-27 12:54:45 (lab_ids 6 and 7).
- **Step 3.** Patient 100047 has one row at its latest time, so one output row (lab_id 1). Patient 100066 has two
  rows at its latest time, the original (6.40) and its correction (5.70), and both are returned. Patient 100144 has
  two repeat draws at its latest time (lab_ids 6 and 7, different `source_record_id` values), and both are returned,
  including lab_id 7 with its NULL `value`. Older rows (lab_ids 2, 5, 8) are not returned.

The real answer has 37,339 rows: one or more per patient with an HbA1c result.

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
