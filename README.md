# Pedestal Health final-round practice

Private interview-prep repo: SQL, Python debugging and data tasks, system design, cross-functional stories.
All data is synthetic and healthcare-flavored, generated from fixed seeds.

## Start here

**Once, on a fresh machine:** run `.\setup.ps1` in PowerShell at the repo root. It installs Python if it's
missing, builds `.venv`, starts the Postgres container, seeds the database, and prints READY.

**Every sitting:**

1. **Warm up, 5-10 min.** Tell Claude "let's study". The ADHD study coach quizzes you on whatever is due.
2. **`python tasks.py next`.** It shows one block, with a first step that takes under 2 minutes, and starts the
   block's clock. Do it, then run `next` again. Two blocks make a full sitting. Keep going if you're in flow.
3. **Wrap up, 5 min.** Tell Claude "I'm done for today". The coach has you teach back what you did and
   schedules your reviews.

**Your work saves itself.** `next`, `done`, `check-sql`, `test` and the other everyday commands commit
everything and push it to GitHub. If the laptop is wiped again, your answers are still there.

## The plan

[`00_plan/queue.md`](00_plan/queue.md) is the whole plan: small blocks in priority order, with no dated days.
Two things are fixed:

- **Tue Oct 13 is mock day.** The mock blocks appear in `next` that morning. Until then, leave SQL 11 and 12,
  debugging 08, data task 04, and design prompt 05 unopened.
- **Interview days.** Add each date with `python tasks.py set-interview 2026-10-15`. On the day itself,
  `next` shows only blocks dated for that day (a short warm-up set), then a review list instead of new work. The day before, it first shows any blocks dated for that
  day (like the mock's gap blocks, dated `@2026-10-14`), then the same list.

## Commands

| Command | What it does |
|---|---|
| `python tasks.py next` | the one block to do now; starts its clock |
| `python tasks.py done` | ticks the block you're on (or `done sql-07` for a specific one) |
| `python tasks.py done --partial "what's left"` | timebox ran out at about 65%: counts as done, and the rest becomes a 10-minute block |
| `python tasks.py timer` | live countdown for the current block, with a beep at halfway and at the end (`timer 2` for any length) |
| `python tasks.py status` | solved count, streak, XP, badges, and progress per strand |
| `python tasks.py board` | opens your board in the browser (see below) |
| `python tasks.py save` | commit and push right now |
| `python tasks.py set-interview DATE ...` | record interview dates (`--clear` to reset) |
| `python tasks.py check-sql 07` | runs `02_sql/solutions/07_*.sql` and compares a SHA-256 of the result with `02_sql/expected/`; ticks `sql-07` on PASS |
| `python tasks.py try-sql 07` | runs your `07_*.sql` on the problem's Example rows and prints the result. The rows live in `02_sql/try/07_*.txt` (written on first run): change values, copy or delete rows, and run it again to see what changes. While the rows match the Example, it says whether you got the Example output. `--reset` restores the Example. The rows load into schema `try_07`, so you can also query them in VS Code after `SET search_path TO try_07;`. Never ticks a block |
| `python tasks.py perf 13` | perf problems: times slow vs. your rewrite, without and with your indexes, and writes the plans to a report |
| `python tasks.py time-sql FILE` | `EXPLAIN (ANALYZE, BUFFERS)` plus the median runtime of any one query |
| `python tasks.py drop-indexes` | removes every index you added to the practice tables |
| `python tasks.py test debugging 03` | runs one exercise's tests (omit the number for all); ticks the block on PASS |
| `python tasks.py test data` / `test screen` / `test all` | other test areas |
| `python tasks.py bench 05` | a debugging exercise's benchmark |
| `python tasks.py gen-data --big 5000000` | big transactions file for the screen rebuild (streaming practice) |
| `python tasks.py gen-data --big-mb 2000` | the 2 GB-scale file for data task 03 |

Set `PRACTICE_AUTOSAVE=0` to turn autosave off. A file over 20 MB is never committed; autosave tells you to
gitignore it instead.

### Feedback, LeetCode style

- **Every finished block gets a verdict.** `done`, a passing `check-sql` or `test` prints a green **Accepted**,
  your time against the timebox, and the XP it earned (a block is worth its timebox in minutes; a coach warm-up
  is worth 10). Then your streak, any new badge, and the badge you're closest to.
- **Streaks forgive a rest day.** Study days in a row count, and one day off between them doesn't break it.
- **Badges** (23 of them) reward finishing, coming back after a break, a second sitting on the same day,
  `done --partial`, and finishing whole sets like all five stories.
- **Coming back to a block?** If its clock already ran out, `next` says welcome back and starts a fresh one.
- **The board** (`python tasks.py board`) is a local page shaped like LeetCode: the block to do now with
  buttons that open its files in VS Code, the study plan as a problem list, a solved ring, a study calendar,
  badges, and recent accepted blocks. Leave the tab open: every `tasks.py` command updates it, and a finished
  block gets confetti and a badge pop-up. `board/data.js` is written locally and never committed.

### Seeing query plans

The Microsoft PostgreSQL extension for VS Code draws plans as a node graph and an icicle chart.

- **Live:** open your solution `.sql`, connect to `practice`, and click **Visualize Query Plan** in the editor
  toolbar.
- **Saved:** `perf` and `time-sql` save each plan to `02_sql/plans/` (gitignored). Open one, then
  Ctrl+Shift+P > **PGSQL: Visualize Query Plan from Editor**. `perf` saves all four variants, so you can compare
  before and after your index.
- **Tables:** in the PostgreSQL sidebar, right-click the `practice` database > **Visualize Schema**.

### How SQL checking works

The checker normalizes every value (numbers to 2 decimals, timestamps to ISO), sorts the rows, and hashes them.
Row order and column names don't matter; **column order does**. On a mismatch it tells you the row and column
counts and **which columns** differ, without showing the answer.

### Answer keys

There are no key branches: the planned `keys`, `mock` and `mock-keys` branches never reached GitHub. The SQL
checker, the tests, and the design rubric grade your work. For anything they don't cover, like design notes
and stories, ask Claude to review your attempt.

## Setup details

`setup.ps1` does all of this. It's here in case you need a step by hand.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
docker run -d --name leetpg --restart unless-stopped -e POSTGRES_PASSWORD=leet -p 5432:5432 -v leetpg-data:/var/lib/postgresql/data postgres:16
python tasks.py setup-db            # creates database `practice`, ~1.5M lab rows, about 40 s
```

The database URL defaults to `postgresql://postgres:leet@localhost:5432/practice`. To use another server:
`$env:PRACTICE_DSN = "postgresql://user:pass@host:5432/practice"`. In DataGrip, connect to localhost:5432 as
`postgres` / `leet`, database `practice`.

`setup-db` is safe to rerun: it rebuilds the tables, and the data comes out identical every time.

## Layout

```
00_plan/            queue.md (the plan), interviews.txt (your interview dates)
01_cross_functional/stories.md         five behavioral stories, as bullets
02_sql/
  perf_lab.sql                         index and EXPLAIN lab (E1-E9)
  schema.sql, seed.py                  shared clinical DB: sites, patients, enrollments, encounters, quarterly_loads, labs
  problems/NN_name.md                  12 problems plus 2 perf problems (13, 14)
  solutions/NN_name.sql                you write here (perf: .sql, .indexes.sql, .answer.md)
  expected/NN_name.sha256              result hashes
  try/NN_name.txt                      Example input rows for try-sql, yours to edit
03_python/
  screen_rebuild/                      tech-screen rebuild with messy data
  debugging/NN_name/                   prompt.md, buggy.py, test_*.py, bench.py for perf exercises
  data_tasks/NN_name/                  prompt.md, data/, solution.py (stub), test_*.py
04_system_design/
  template.md, rubric.md (with your score log), prompts/NN_name.md, answers/ (your typed notes)
coach/              the ADHD study coach's profile, review schedule, session log, and notes
board/index.html    your board; tasks.py writes board/data.js next to it
setup.ps1           one-command setup
```

## The database in one paragraph

12 sites (S10-S12 onboard late) send quarterly batches. `labs` is append-only: a correction is the same
`(site_id, source_record_id)` resent in a later batch with a later `loaded_at`. S04 and S09 report SI units,
S07 switched hemoglobin to g/L in mid-2025, and S06 writes `mg/dl`. There are repeat draws with identical
timestamps, decimal-slip values, missing and rejected quarterly submissions, and enrollment periods that overlap,
touch, or nest. Every planted problem is there for an exercise; the docstring in `02_sql/seed.py` lists them all.

## Ground rules

- Your attempts live on `main`, and autosave commits them there. Reference solutions never go on `main`; if
  Claude writes one, it goes on a `keys` branch and starts with `REFERENCE SOLUTION (keys branch only)`.
- Each block has a timebox. When it runs out, `done --partial` and move on: finishing under time is the skill.
- This repo is private and holds personal stories. Keep it private.
