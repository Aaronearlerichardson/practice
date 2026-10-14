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

**Goal:** return one row per site S03 patient, with four columns holding that patient's most recently collected
2025 `value` for GLU, HBA1C, CREAT and K. Use only the latest version of each record.

1. **Keep site S03.** Use only `labs` rows with `site_id = 'S03'`.
2. **Keep the latest version of each record.** A record is one `source_record_id`, and each row is one version of
   it. For each `source_record_id`, keep the row with the latest `loaded_at`. When several rows share that
   `loaded_at`, keep the one with the highest `lab_id`. Run this on all step 1 rows, before the step 3 filters.
3. **Keep four tests collected in 2025.** Of the step 2 rows, keep those with `test_code` in (`'GLU'`, `'HBA1C'`,
   `'CREAT'`, `'K'`) and `collected_at >= '2025-01-01'` and `collected_at < '2026-01-01'`. Rows whose `value` is
   NULL stay.
4. **Take each patient's latest result per test.** For each (`patient_id`, `test_code`), take the step 3 row with
   the latest `collected_at`. When several share it, take the one with the highest `lab_id`. This gives at most one
   row per patient per test.
5. **Pivot the tests into columns.** Return one row per `patient_id` that has at least one step 3 row. Fill each
   test's column with the `value` of that patient's step 4 row for the test:
   - `glu`: from the step 4 row with `test_code = 'GLU'`
   - `hba1c`: from the step 4 row with `test_code = 'HBA1C'`
   - `creat`: from the step 4 row with `test_code = 'CREAT'`
   - `k`: from the step 4 row with `test_code = 'K'`

   A column is NULL when the patient has no step 4 row for that test, or when that row's `value` is NULL (an older
   non-NULL result does not replace it).

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | one row per S03 patient with at least one step 3 row |
| 2 | glu | from step 5: `value` of the step 4 row with `test_code = 'GLU'` |
| 3 | hba1c | from step 5: `value` of the step 4 row with `test_code = 'HBA1C'` |
| 4 | creat | from step 5: `value` of the step 4 row with `test_code = 'CREAT'` |
| 5 | k | from step 5: `value` of the step 4 row with `test_code = 'K'` |

## Example

Input `labs` (only the columns this task reads):

```text
+--------+------------+---------+------------------+-----------+--------+---------------------+---------------------+
| lab_id | patient_id | site_id | source_record_id | test_code | value  | collected_at        | loaded_at           |
+--------+------------+---------+------------------+-----------+--------+---------------------+---------------------+
| 1      | 100013     | S03     | S03-L0000009     | GLU       | 120.00 | 2024-12-30 10:05:00 | 2025-02-12 16:09:52 |
| 2      | 100003     | S03     | S03-L0000001     | GLU       | 140.00 | 2025-03-10 08:30:00 | 2025-05-15 19:09:06 |
| 3      | 100003     | S03     | S03-L0000002     | GLU       | 98.00  | 2025-01-20 07:45:00 | 2025-05-15 19:09:06 |
| 4      | 100003     | S03     | S03-L0000005     | NA        | 139.00 | 2025-04-01 11:00:00 | 2025-05-15 19:09:06 |
| 5      | 100007     | S03     | S03-L0000006     | CREAT     | 1.10   | 2025-02-14 13:20:00 | 2025-05-15 19:09:06 |
| 6      | 100007     | S03     | S03-L0000007     | K         | 4.90   | 2025-03-03 09:10:00 | 2025-05-15 19:09:06 |
| 7      | 100003     | S03     | S03-L0000001     | GLU       | 104.00 | 2025-03-10 08:30:00 | 2025-08-08 04:23:12 |
| 8      | 100003     | S03     | S03-L0000003     | HBA1C     | 6.80   | 2025-06-02 09:15:00 | 2025-08-08 04:23:12 |
| 9      | 100003     | S03     | S03-L0000004     | HBA1C     | 7.10   | 2025-06-02 09:15:00 | 2025-08-08 04:23:12 |
| 10     | 100007     | S03     | S03-L0000008     | K         | NULL   | 2025-07-19 14:40:00 | 2025-08-08 04:23:12 |
| 11     | 100025     | S07     | S07-L0000034     | GLU       | 210.00 | 2025-09-01 08:00:00 | 2025-10-29 21:26:04 |
+--------+------------+---------+------------------+-----------+--------+---------------------+---------------------+
```

Output:

```text
+------------+--------+-------+-------+------+
| patient_id | glu    | hba1c | creat | k    |
+------------+--------+-------+-------+------+
| 100003     | 104.00 | 7.10  | NULL  | NULL |
| 100007     | NULL   | NULL  | 1.10  | NULL |
+------------+--------+-------+-------+------+
```

Explanation:

- **Step 1.** lab_id 11 is dropped: its `site_id` is `'S07'`. Patient 100025 has no other rows, so it gets no
  output row.
- **Step 2.** `S03-L0000001` has two versions: lab_id 7 (loaded 2025-08-08) is later than lab_id 2 (loaded
  2025-05-15), so lab_id 7 (104.00) is kept and lab_id 2 (140.00) is dropped. Every other record has one version.
- **Step 3.** lab_id 1 is dropped: it was collected in 2024. lab_id 4 is dropped: `NA` is not one of the four tests.
  lab_id 10 stays even though its `value` is NULL. Patient 100013's only row was lab_id 1, so 100013 gets no output
  row.
- **Step 4.** Patient 100003 has two GLU rows: lab_id 7 (collected 2025-03-10) is later than lab_id 3 (collected
  2025-01-20), so lab_id 7 is taken. Patient 100003's two HBA1C rows share `collected_at` 2025-06-02 09:15:00, so
  lab_id 9 (the higher `lab_id`) is taken over lab_id 8. Patient 100007 has two K rows: lab_id 10 (collected
  2025-07-19) is later than lab_id 6 (collected 2025-03-03), so lab_id 10 is taken.
- **Step 5.** 100003: `glu` = 104.00 (lab_id 7) and `hba1c` = 7.10 (lab_id 9). Its `creat` and `k` are NULL
  because it has no CREAT or K rows. 100007: `creat` = 1.10 (lab_id 5). Its `k` is NULL because lab_id 10's
  `value` is NULL; the older 4.90 (lab_id 6) does not replace it. Its `glu` and `hba1c` are NULL because it has no
  GLU or HBA1C rows.

The real answer has 2839 rows, one per S03 patient with at least one step 3 row.

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
