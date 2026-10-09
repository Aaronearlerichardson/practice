# Pedestal Health final-round practice

Private interview-prep repo: SQL, Python debugging and data tasks, system design, cross-functional stories.
All data is synthetic and healthcare-flavored, generated from fixed seeds.

**What to do today:** [`00_plan/schedule.md`](00_plan/schedule.md).

## Branches

| Branch | Holds | When to check it out |
|---|---|---|
| `main` | exercises, data, generators, tests, checkers. **No solutions.** | always |
| `keys` | `main` plus reference solutions, SQL reference queries, design model answers | only after you've attempted something |
| `mock` | `main` plus `mock/`: an unseen full mock | **Tue, Oct 13**, not before |
| `mock-keys` | `mock` plus the mock's answers | after the mock |

Read a single key without switching branches:

```powershell
git show keys:03_python/debugging/03_slow_encounter_dedup/buggy.py
git show keys:02_sql/reference/07_continuous_enrollment_islands.sql
```

Do your work on `main` (or a branch off it). Don't merge `keys` into `main`.

## One-time setup (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

docker start leetpg                 # the local Postgres 16 container
python tasks.py setup-db            # creates database `practice`, ~1.5M lab rows, about 40 s
python tasks.py gen-data            # regenerates the file-based exercise data (already committed)
```

The database URL defaults to `postgresql://postgres:leet@localhost:5432/practice`. To use another server:
`$env:PRACTICE_DSN = "postgresql://user:pass@host:5432/practice"`. In DataGrip, add the `practice` database
on the same connection you use for LeetCode.

`setup-db` is safe to rerun: it rebuilds the tables, and the data comes out identical every time.

## Commands

| Command | What it does |
|---|---|
| `python tasks.py check-sql 07` | runs `02_sql/solutions/07_*.sql` and compares a SHA-256 of the result with `02_sql/expected/` |
| `python tasks.py perf 13` | perf problems: times slow vs. your rewrite, without and with your indexes, and writes the plans to a report |
| `python tasks.py time-sql FILE` | `EXPLAIN (ANALYZE, BUFFERS)` plus the median runtime of any one query |
| `python tasks.py drop-indexes` | removes every index you added to the practice tables |
| `python tasks.py test debugging 03` | runs one exercise's tests; omit the number for all of them |
| `python tasks.py test data` / `test screen` / `test all` | other test areas |
| `python tasks.py bench 05` | a debugging exercise's benchmark |
| `python tasks.py gen-data --big 5000000` | big transactions file for the screen rebuild (streaming practice) |
| `python tasks.py gen-data --big-mb 2000` | the 2 GB-scale file for data task 03 |

### How SQL checking works

The checker normalizes every value (numbers to 2 decimals, timestamps to ISO), sorts the rows, and hashes them.
Row order and column names don't matter; **column order does**. On a mismatch it tells you the row and column
counts and **which columns** differ, without showing the answer.

## Layout

```
00_plan/            schedule.md (daily plan), FRIDAY.md (Friday's task sheet from the kit)
01_cross_functional/stories.md         five behavioral stories worksheet
02_sql/
  perf_lab.sql                         index and EXPLAIN lab (E1-E9)
  schema.sql, seed.py                  shared clinical DB: sites, patients, enrollments, encounters, quarterly_loads, labs
  problems/NN_name.md                  12 problems plus 2 perf problems (13, 14)
  solutions/NN_name.sql                you write here (perf: .sql, .indexes.sql, .answer.md)
  expected/NN_name.sha256              result hashes
03_python/
  screen_rebuild/                      tech-screen rebuild with messy data (from the kit)
  debugging/NN_name/                   prompt.md, buggy.py, test_*.py, bench.py for perf exercises
  data_tasks/NN_name/                  prompt.md, data/, solution.py (stub), test_*.py
04_system_design/
  template.md, rubric.md, prompts/NN_name.md
```

## The database in one paragraph

12 sites (S10-S12 onboard late) send quarterly batches. `labs` is append-only: a correction is the same
`(site_id, source_record_id)` resent in a later batch with a later `loaded_at`. S04 and S09 report SI units,
S07 switched hemoglobin to g/L in mid-2025, and S06 writes `mg/dl`. There are repeat draws with identical
timestamps, decimal-slip values, missing and rejected quarterly submissions, and enrollment periods that overlap,
touch, or nest. Every planted problem is there for an exercise; the docstring in `02_sql/seed.py` lists them all.

## Ground rules for this repo

- `main` never contains solutions. Every reference carries the marker `REFERENCE SOLUTION (keys branch only)`,
  so `git grep "REFERENCE SOLUTION" main` must print nothing.
- Each prompt states its timebox at the top. Respect it.
- This repo is private and will hold personal stories. Keep it private.
