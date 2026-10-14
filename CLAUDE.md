# Notes for Claude

Aaron's prep for final-round data engineering interviews at Pedestal Health (Oct 15 and 16, 2026). The repo is built
to be ADHD-friendly: small blocks, one next step, visible progress, and autosave.

## Study sessions go through the ADHD study coach

- When Aaron says "let's study", "quiz me", "I'm done for today", or "how am I doing", hand it to the
  `adhd-study-coach` agent.
- Tell the coach its DATA_DIR is this repo's `coach/` folder (`C:\Users\Jakda\git\practice\coach`), not
  `~/.adhd-study-coach/` or the plugin data directory. `coach/` is committed and pushed, so it survives a wipe.
- The coach is the only writer of `coach/profile.json`, `review-schedule.json`, `sessions.log.jsonl` and
  `coach/notes/`. `tasks.py` only appends `coach/blocks-done.jsonl` (blocks finished, with minutes and
  leftovers), which the coach should read at wrap-up.
- After a coach session, run `.venv/Scripts/python.exe tasks.py save` so its files reach GitHub.
- Aaron finishes more with LeetCode-style feedback. When handing off to the coach, ask it to open each graded
  warm-up answer with a verdict line: `✓ Accepted` (solid), `◐ Partially accepted` (shaky) or `○ Not yet`
  (blank), and to mention `python tasks.py board` at wrap-up.

## Feedback layer

- `tasks.py` prints an Accepted verdict, XP, streak and new badges when a block ticks, and rewrites
  `board/data.js` (gitignored) after every command for `board/index.html`. All of it is computed from
  `queue.md`, `coach/blocks-done.jsonl` and the coach's session log, so there's no extra state to keep in sync.
  Badges already announced are remembered in `.practice_state.json`.
- Badge definitions live in `progress()` and `BADGE_SETS`. A set badge only appears if its block ids exist in
  the queue, so renaming blocks quietly drops it.
- Keep feedback language positive. A streak can start or grow, but it never "breaks" or gets "lost".

## The plan

- `00_plan/queue.md` is the plan, driven by `tasks.py next` and `done`. Don't bring back dated day-by-day
  schedules, or any "behind" or overdue language.
- Add work as blocks of 15-25 minutes: a timebox, a first step under 2 minutes that names a file, and a
  "Done when". Keep strands mixed so a two-block sitting touches two of them.
- Interview days (`00_plan/interviews.txt`) are review-only in `next`. The day before, `next` shows only blocks
  dated for that day (`@YYYY-MM-DD` in the title), so date any mock-gap blocks `@2026-10-14`.
- Each block can end with a "New to this?" line pointing to its section in `00_plan/background.md`.
- Shells here don't activate the venv: run `.venv/Scripts/python.exe tasks.py ...`.

## Problems

- Every problem opens with what it reads, LeetCode-style, before the task: each table or input and its columns,
  with types and notes. SQL problems have a `## Tables` section under the header line (generated from
  `02_sql/schema.sql`), Python problems an `## Input` section. Never deviate from this, including for new problems.
- Write every rule the way LeetCode does: name the exact columns and literal values it uses (`site_id = 'S07'`,
  "for each (`site_id`, `source_record_id`)", `loaded_at <= '2025-10-01 00:00:00'`). Define any term such as
  "record", "latest version" or "canonical unit" in column terms right where it's used. Each output column's
  note says which column or expression it comes from.
- Problems stand alone. Never refer to another problem ("problem 08's rule", "same as the screen", "from task
  01"). Restate the rule in full.
- The SQL problem files are latin-1 with CRLF. Edit them with a script that keeps that encoding.

## Answers

- Don't show a solution before Aaron has attempted the problem. Review attempts when asked.
- No reference solutions on `main` (see the README's ground rules).
