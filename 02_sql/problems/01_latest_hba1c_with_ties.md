# 01. Latest HbA1c per patient, keeping ties

**Timebox: 15 min** · Tables: `labs` · Write your answer in `02_sql/solutions/01_latest_hba1c_with_ties.sql`

A diabetes study needs each patient's most recent HbA1c. Some patients have two results with the **same**
`collected_at` (repeat draws, or a correction resent by the site). Downstream wants to see all of them so a
person can adjudicate, so don't pick one arbitrarily.

## Task

For `test_code = 'HBA1C'`, return every row whose `collected_at` equals that patient's latest HbA1c `collected_at`.
Use `labs` as loaded. Corrections are not deduplicated here; that comes in problem 08.

## Output columns

| # | column | notes |
|---|---|---|
| 1 | patient_id | |
| 2 | lab_id | |
| 3 | collected_at | |
| 4 | value | as stored (may be NULL) |

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
