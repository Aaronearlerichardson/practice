# Schedule: Fri Oct 9 to the final round (Oct 14-22)

Rule of thumb: timebox everything. When a timebox runs out, stop, note what you'd do next, and move on.
Interview skill is finishing under time, not finishing eventually.

| Day | Focus |
|---|---|
| Fri, Oct 9 | Stories, SQL perf lab plus LeetCode 178/184/1158, screen rebuild in pandas |
| Sat, Oct 10 | System design template and prompt 1 (20 min, timed); standard-library streaming rebuild; LeetCode 721 and 981; SQL problems 1-3 |
| Sun, Oct 11 | Debugging exercises 1-8; SQL problems 4-8 plus EXPLAIN on my job-crawler SQLite DB; tell stories aloud |
| Mon, Oct 12 | System design prompt 2; data tasks 1-2; SQL problems 9-12 and both performance problems |
| Tue, Oct 13 | Full mock from the `mock` branch |
| Oct 14 until interviews | Daily: 1 SQL, 1 Python, 1 design prompt, story run-through. Nothing new the night before. |

## Fri, Oct 9 (about 4.5 h; see `FRIDAY.md` for the cut order)

1. **Stories (1.5 h):** `01_cross_functional/stories.md`. Write all five, then tell each out loud once.
2. **SQL perf lab (1.5 h):** run `02_sql/perf_lab.sql` in DataGrip against the `practice` database (it creates
   its own `lab_events` table). Write a prediction before every EXPLAIN. Then LeetCode 178, 184, 1158.
3. **Screen rebuild, pandas (1.5 h):** `03_python/screen_rebuild/README.md`. Write `standardize.py` and three
   tests, then `python tasks.py test screen`.

## Sat, Oct 10

1. **System design (1 h):** read `04_system_design/template.md` and `rubric.md`. Then prompt 01 as a **20-minute
   speed round**: timer on, talk out loud, sketch on paper. Self-grade with the rubric and log the score.
2. **Screen rebuild, standard library only (1 h):** redo `standardize.py` with `csv` and no pandas, streaming
   row by row. Then `python tasks.py gen-data --big 5000000` and run it on the big file with constant memory.
3. **LeetCode 721, 981 (45 min).**
4. **SQL 01-03 (1 h):** `02_sql/problems/01_*.md` ... `03_*.md`; `python tasks.py check-sql 01`, and so on.

## Sun, Oct 11

1. **Debugging 01-08 (2 h):** `03_python/debugging/`. Read only `prompt.md`, then run the tests and fix.
   `python tasks.py test debugging 03`, `python tasks.py bench 03`. Narrate as you go.
2. **SQL 04-08 (1.5 h).**
3. **EXPLAIN on your job-crawler SQLite DB (20 min):** SQLite uses `EXPLAIN QUERY PLAN <query>`. Find one
   query that does `SCAN table`, add an index, and confirm it becomes `SEARCH table USING INDEX`. That gives you
   a real "I sped up a query" example from your own project.
4. **Stories out loud (30 min):** all five, timed at 2 minutes each, recorded on your phone if you can stand it.

## Mon, Oct 12

1. **System design prompt 02 (45 min, full length),** then grade with the rubric.
2. **Data tasks 01-02 (1.5 h):** `03_python/data_tasks/01_*`, `02_*`. `python tasks.py test data 01`.
3. **SQL 09-12 (1.5 h),** then **13 and 14 (perf, 50 min):** `python tasks.py perf 13`, then write the answer.md.
4. If time remains: data tasks 03-04.

## Tue, Oct 13: full mock

```powershell
git switch mock
Get-Content mock\README.md
```

Follow `mock/README.md` exactly: real timeboxes, no notes, no keys. Afterwards, compare with the
`mock-keys` branch and write down the three biggest gaps.

## Oct 14 until the interviews (daily, about 2 h)

- 1 SQL problem (redo one you missed, or a LeetCode problem from the list below), 20 min.
- 1 Python item (a debugging exercise or a data task you haven't done), 30 min.
- 1 design prompt (03, 04, 05, then repeat 01 and 02), 45 min, graded.
- A story run-through: all five, plus 2 questions from `mock/cross_functional.md` (after the mock).
- **The night before an interview: nothing new.** Reread your stories, the rubric red flags, and your perf answers.

## Reduced LeetCode list

SQL:
[178 Rank Scores](https://leetcode.com/problems/rank-scores/) ·
[184 Department Highest Salary](https://leetcode.com/problems/department-highest-salary/) ·
[1158 Market Analysis I](https://leetcode.com/problems/market-analysis-i/) ·
[1393 Capital Gain/Loss](https://leetcode.com/problems/capital-gainloss/) ·
[1179 Reformat Department Table](https://leetcode.com/problems/reformat-department-table/) ·
[1795 Rearrange Products Table](https://leetcode.com/problems/rearrange-products-table/) ·
[1965 Employees With Missing Information](https://leetcode.com/problems/employees-with-missing-information/) ·
[183 Customers Who Never Order](https://leetcode.com/problems/customers-who-never-order/) ·
[601 Human Traffic of Stadium](https://leetcode.com/problems/human-traffic-of-stadium/) ·
[262 Trips and Users](https://leetcode.com/problems/trips-and-users/)

Python:
[721 Accounts Merge](https://leetcode.com/problems/accounts-merge/) ·
[981 Time Based Key-Value Store](https://leetcode.com/problems/time-based-key-value-store/) ·
[210 Course Schedule II](https://leetcode.com/problems/course-schedule-ii/) ·
[56 Merge Intervals](https://leetcode.com/problems/merge-intervals/) ·
[128 Longest Consecutive Sequence](https://leetcode.com/problems/longest-consecutive-sequence/) ·
[692 Top K Frequent Words](https://leetcode.com/problems/top-k-frequent-words/) ·
[560 Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/) ·
[146 LRU Cache](https://leetcode.com/problems/lru-cache/)

Why these: 981 is the "as of" lookup in Python (compare SQL 12), 56 is gaps and islands (compare SQL 07),
1795 and 1179 are unpivot and pivot (SQL 05 and 10), and 601 is consecutive-row islands.
