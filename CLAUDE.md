# Notes for Claude

Aaron's prep for final-round data engineering interviews at Pedestal Health (Oct 14-22, 2026). The repo is built
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

## The plan

- `00_plan/queue.md` is the plan, driven by `tasks.py next` and `done`. Don't bring back dated day-by-day
  schedules, or any "behind" or overdue language.
- Add work as blocks of 15-25 minutes: a timebox, a first step under 2 minutes that names a file, and a
  "Done when". Keep strands mixed so a two-block sitting touches two of them.
- Shells here don't activate the venv: run `.venv/Scripts/python.exe tasks.py ...`.

## Answers

- Don't show a solution before Aaron has attempted the problem. Review attempts when asked.
- No reference solutions on `main` (see the README's ground rules).
