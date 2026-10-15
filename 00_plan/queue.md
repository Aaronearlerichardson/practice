# The queue

You don't need to read this file. Run `python tasks.py next`: it shows the one block to do now and starts its clock.

Blocks are in priority order, with the strands mixed so each sitting touches two of them. SQL checks and tests tick
their blocks off by themselves. For anything else, run `python tasks.py done`. Your work saves to GitHub as you go.

**One sitting:** warm-up with the coach (tell Claude "let's study"), then 2 blocks, then wrap-up ("I'm done for today").
Keep going if you're in flow. **Timebox ran out and it's about 65% there?** That counts as done:
`python tasks.py done --partial "what's left"`.

**New to a problem's topic?** `00_plan/background.md` has a short video or reading for each concept. A block's
"New to this?" line names the section.

## Done

The Oct 11 reinstall deleted the files from Day 1, but not what you learned. Rewriting the stories from memory is
the review, which is the best-evidenced way to study, and the coach already has it due.

- [x] `story-drafts` **All five stories, first draft** · Fri Oct 9
- [x] `sql-perf-lab` **SQL index and EXPLAIN lab, E1-E9 with predictions** · Fri Oct 9
- [x] `lc-178-184-1158` **LeetCode 178, 184, 1158** · Fri Oct 9
  Your accepted submissions are still on leetcode.com under Submissions.

## Core

- [x] `setup` **Get the tools back after the reinstall** · 10 min
  Start: in PowerShell at the repo root, run `.\setup.ps1`.
  Done when: it prints READY. It ticks this block itself.
- [x] `debug-01` **Debugging 01: QC flags that won't go away** · 10 min
  Start: read `03_python/debugging/01_qc_flags_leak/prompt.md` (not buggy.py yet) and say what you suspect.
  Done when: `python tasks.py test debugging 01` passes. That ticks it.
  New to this? `00_plan/background.md`: the three Toolkit sections, once (18 min), then Names, references and mutable objects (10 min).
- [ ] `design-template` **The design template's shape** · 15 min
  Start: open `04_system_design/template.md` and read only the minute-budget table.
  Done when: you've read sections 0-3, closed the file, and written the section names and minutes on paper from memory.
  New to this? `00_plan/background.md`: How a data-engineering design interview runs (11 min).
- [ ] `story-1` **Story 1: turning a vague need into the `ieeg` package** · 15 min
  Start: open `01_cross_functional/stories.md` and write story 1's Situation line from memory. Don't scroll down.
  Done when: bullets written blind, checked against Known facts, told out loud once on `python tasks.py timer 2`.
- [ ] `story-2` **Story 2: moving the lab from .dat files to BIDS** · 15 min
  Start: in `01_cross_functional/stories.md`, write the Situation line for story 2 from memory.
  Done when: bullets written blind, checked against Known facts, told out loud once on a 2:00 timer.
- [ ] `story-3` **Story 3: the mne-bids regression CI missed** · 15 min
  Start: in `01_cross_functional/stories.md`, write the Situation line for story 3 from memory.
  Done when: bullets written blind, checked against Known facts, told out loud once on a 2:00 timer.
- [ ] `sql-02` **SQL 02: top providers per site, RANK vs. DENSE_RANK** · 15 min
  Start: open `02_sql/problems/02_top_providers_rank_vs_dense.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 02` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Ranking window functions (8 min).
- [ ] `story-4` **Story 4: Duke Box vs. the offsite server** · 15 min
  Start: in `01_cross_functional/stories.md`, write the Situation line for story 4 from memory.
  Done when: bullets written blind, checked against Known facts, told out loud once on a 2:00 timer.
- [ ] `design-01` **Design 01: quarterly EHR ingestion, speed round** · 20 min
  Start: open `04_system_design/prompts/01_quarterly_ehr_ingestion.md`, run `python tasks.py timer`, say the opener aloud.
  Done when: every section sketched on paper while talking, or time's up. Note which section you hit at minute 10.
  New to this? `00_plan/background.md`: Landing zone and layers, Validation at the boundary, and Idempotent loads (22 min). Retries and Iceberg commits if you have time.
- [ ] `design-01-grade` **Grade design 01** · 10 min
  Start: open `04_system_design/rubric.md` next to your paper.
  Done when: one row added to the rubric's Score log. For feedback, type your notes into `04_system_design/answers/01.md`.
- [ ] `story-5` **Story 5: labmates' pipeline requests vs. your paper** · 15 min
  Start: in `01_cross_functional/stories.md`, pick the one real episode and write its Situation line.
  Done when: bullets written, told out loud once on a 2:00 timer.
- [ ] `story-aloud` **All five stories out loud, back to back** · 15 min
  Start: phone voice recorder on, `python tasks.py timer 2`, story 1.
  Done when: all five told, each under about 2:15. Listen back to one.
- [ ] `data-01-plan` **Data task 01: three sites, one lab table (plan)** · 10 min
  Start: read `03_python/data_tasks/01_multisite_lab_join/prompt.md`.
  Done when: you've said the edge cases out loud and stubbed the functions in `solution.py`.
  New to this? `00_plan/background.md`: Stop pandas guessing types and NaNs, Parsing dates with strptime, and How merges multiply rows (11 min).
- [ ] `data-01` **Data task 01: build it** · 25 min
  Start: run `python tasks.py test data 01 -v` and read the first failure.
  Done when: `python tasks.py test data 01` passes. That ticks it.
- [ ] `sql-13` **SQL 13 (perf): rewrite a slow query and add an index** · 25 min
  Start: open `02_sql/problems/13_perf_sargable_rewrite.md`. Before running anything, write which plan node does the work.
  Done when: `python tasks.py perf 13` says the rewrite returns the same rows. That ticks it.
  New to this? `00_plan/background.md`: Sargable filters and Multi-column index order (12 min). Reading EXPLAIN plans too, if plans are still fuzzy.
- [ ] `sql-13-explain` **SQL 13: the interview explanation** · 10 min
  Start: copy the timing table from `02_sql/solutions/13_perf_sargable_rewrite.report.md` into its `.answer.md`.
  Done when: the answer has the plan before and after, the timings, and the three or four sentences you'd say.
- [ ] `debug-03` **Debugging 03: encounter dedup is timing out** · 10 min
  Start: read `03_python/debugging/03_slow_encounter_dedup/prompt.md`, then run `python tasks.py bench 03`.
  Done when: `python tasks.py test debugging 03` passes. That ticks it.
  New to this? `00_plan/background.md`: Big-O: reading a timing curve, and Profiling with cProfile (13 min).
- [ ] `debug-05` **Debugging 05: unit normalization is the slowest step** · 15 min
  Start: read `03_python/debugging/05_lab_unit_normalize/prompt.md`, then run `python tasks.py bench 05`.
  Done when: `python tasks.py test debugging 05` passes. That ticks it.
  New to this? `00_plan/background.md`: Profiling with cProfile, and Vectorizing pandas (13 min).
- [ ] `design-03` **Design 03: late corrections and "as of" datasets, speed round** · 20 min
  Start: open `04_system_design/prompts/03_late_corrections_as_of.md`, run `python tasks.py timer`, say the opener aloud.
  Done when: every section sketched on paper while talking, or time's up.
  New to this? `00_plan/background.md`: As-of history: two clocks, and Change history with SCD Type 2 (16 min). Snapshots, tags and retention if you have time.
- [ ] `design-03-grade` **Grade design 03** · 10 min
  Start: open `04_system_design/rubric.md` next to your paper.
  Done when: one row added to the Score log.
- [ ] `sql-09` **SQL 09: plausibility after unit normalization** · 25 min
  Start: open `02_sql/problems/09_plausibility_after_unit_normalization.md` and list the unit traps it names.
  Done when: `python tasks.py check-sql 09` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: CTE steps, CASE, and VALUES lookup tables (5 min).
- [ ] `data-02-plan` **Data task 02: the site resent Q1 (plan)** · 10 min
  Start: read `03_python/data_tasks/02_idempotent_reload/prompt.md`.
  Done when: you've said what "idempotent" means for this load and stubbed the functions in `solution.py`.
  New to this? `00_plan/background.md`: What makes a load idempotent (4 min).
- [ ] `data-02` **Data task 02: build it** · 25 min
  Start: run `python tasks.py test data 02 -v` and read the first failure.
  Done when: `python tasks.py test data 02` passes. That ticks it.
  New to this? `00_plan/background.md`: Transactions in sqlite3, and File checksums with hashlib (4 min).
- [ ] `sql-10` **SQL 10: pivot test codes into columns** · 20 min
  Start: open `02_sql/problems/10_pivot_latest_labs.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 10` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Conditional aggregation and pivot (8 min).
- [ ] `debug-06` **Debugging 06: lab profiling job runs out of memory** · 12 min
  Start: read `03_python/debugging/06_lab_extract_memory/prompt.md`, then run `python tasks.py bench 06`.
  Done when: `python tasks.py test debugging 06` passes. That ticks it.
  New to this? `00_plan/background.md`: Memory: dtypes and processing in chunks (5 min).
- [ ] `design-04` **Design 04: pharma dataset delivery, speed round** · 20 min
  Start: open `04_system_design/prompts/04_pharma_dataset_delivery.md`, run `python tasks.py timer`, say the opener aloud.
  Done when: every section sketched on paper while talking, or time's up.
  New to this? `00_plan/background.md`: HIPAA de-identification, and Delivering releases (15 min).
- [ ] `design-04-grade` **Grade design 04** · 10 min
  Start: open `04_system_design/rubric.md` next to your paper.
  Done when: one row added to the Score log.
- [ ] `sql-14` **SQL 14 (perf): rewrite a correlated subquery** · 25 min
  Start: open `02_sql/problems/14_perf_correlated_subquery.md`. Before running anything, predict the slow plan.
  Done when: `python tasks.py perf 14` says the rewrite returns the same rows. That ticks it.
  New to this? `00_plan/background.md`: Correlated subqueries vs. joins (6 min).
- [ ] `sql-14-explain` **SQL 14: the interview explanation** · 10 min
  Start: copy the timing table from `02_sql/solutions/14_perf_correlated_subquery.report.md` into its `.answer.md`.
  Done when: the answer has the plan before and after, the timings, and the three or four sentences you'd say.
- [ ] `data-03-plan` **Data task 03: two gigabytes, ten megabytes (plan)** · 10 min
  Start: read `03_python/data_tasks/03_streaming_aggregates/prompt.md`.
  Done when: you've said which aggregates can stream in one pass and which can't, and stubbed `solution.py`.
  New to this? `00_plan/background.md`: Generators, and Streaming CSV with the csv module (18 min).
- [ ] `data-03` **Data task 03: build it** · 25 min
  Start: run `python tasks.py test data 03 -v` and read the first failure.
  Done when: `python tasks.py test data 03` passes. That ticks it.
  New to this? `00_plan/background.md`: Measuring peak memory (3 min).
- [ ] `sql-05` **SQL 05: fill rate per column per site** · 20 min
  Start: open `02_sql/problems/05_demographic_fill_rates.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 05` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Fill rates, and Unpivot and LATERAL (9 min).

## Mock day: Tue Oct 13

These blocks stay hidden until Oct 13, then `next` puts them first. Until then, don't open SQL 11 or 12,
debugging 08, data task 04, or design prompt 05. On the day: no notes, no Claude, real timeboxes, and a
5-minute break away from the screen between parts.

- [x] `mock-1` **Mock part 1: SQL** · 45 min @2026-10-13
  SQL 11 (20 min), then SQL 12 (25 min). Check each with `python tasks.py check-sql 11` and `check-sql 12`.
  Done when: both timeboxes are used, pass or not.
- [ ] `mock-2` **Mock part 2: Python** · 55 min @2026-10-13
  Debugging 08 (15 min), then data task 04 (40 min). `python tasks.py test debugging 08`, `test data 04`.
  Done when: both timeboxes are used, pass or not.
- [ ] `mock-3` **Mock part 3: design 05, full length** · 45 min @2026-10-13
  `04_system_design/prompts/05_data_quality_monitoring.md`, out loud the whole time, paper only.
  Done when: 45 minutes are used.
- [ ] `mock-4` **Mock part 4: behavioral** · 15 min @2026-10-13
  Two of your stories plus two short-answer questions from the end of `01_cross_functional/stories.md`, recorded.
  Done when: all four are said out loud, about 2 minutes each.
- [ ] `mock-5` **Mock review** · 20 min @2026-10-13
  Grade design 05 with the rubric. Type your design notes into `04_system_design/answers/05.md` and ask Claude to review them.
  Done when: your three biggest gaps are written in `00_plan/mock_gaps.md`. Ask Claude to turn them into blocks in the
  Wed Oct 14 section below, dated `@2026-10-14`.

## Wed Oct 14, tonight: the Python and SQL set

Thursday is the Python and SQL rounds. This set covers the patterns they ask most, alternating SQL and Python,
most useful first. Stop at midnight wherever you are: what's left was the lowest priority.

**First, 1 minute:** start Docker Desktop. The repo's SQL checks need the `leetpg` container. The first block is on
leetcode.com, so it doesn't wait for Docker. On LeetCode's SQL problems, pick PostgreSQL in the language menu.

- [x] `lc-sql-basics` **LeetCode 1581 and 1193: anti-join, then counts per month** · 15 min @2026-10-14
  1581 (LEFT JOIN, keep rows where the right side IS NULL), then 1193 (GROUP BY month with SUM(CASE ...)).
  Start: open https://leetcode.com/problems/customer-who-visited-but-did-not-make-any-transactions/ and read the tables.
  Done when: both Accepted on LeetCode. Then `python tasks.py done`.
  New to this? `00_plan/background.md`: Anti-joins, and Conditional aggregation and pivot.
- [x] `screen-pandas` **Screen rebuild in pandas: standardize.py** · 25 min @2026-10-14
  Did this on Friday? Run `python tasks.py done screen-pandas` and move on.
  Start: read the Rules table in `03_python/screen_rebuild/README.md`, then look at the products table.
  Done when: your counts match the README's "Check yourself" section.
  New to this? `00_plan/background.md`: How merges multiply rows, and Exact vs. conflicting duplicates (10 min).
- [x] `sql-08` **SQL 08: dedupe corrected lab records** · 20 min @2026-10-14
  Start: open `02_sql/problems/08_dedupe_lab_corrections.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 08` prints PASS. That ticks it. Then say out loud how Snowflake (Pedestal's
  warehouse) shortens it: `QUALIFY ROW_NUMBER() OVER (...) = 1` with no subquery. Write the subquery form in the interview.
  New to this? `00_plan/background.md`: Latest version per key (4 min).
- [ ] `lc-py-hashmaps` **LeetCode 49 and 347: group and count with dicts** · 20 min @2026-10-14
  49 Group Anagrams (`defaultdict(list)` keyed on a normalized value), then 347 Top K Frequent Elements (`Counter`, then
  `sorted` with a key or `heapq.nlargest`).
  Start: open https://leetcode.com/problems/group-anagrams/ and say out loud what the dict key is.
  Done when: both Accepted on LeetCode. Then `python tasks.py done`.
  New to this? `00_plan/background.md`: Sorting with a key (6 min).
- [ ] `sql-03` **SQL 03: quarter-over-quarter lab volume with LAG** · 15 min @2026-10-14
  Start: open `02_sql/problems/03_qoq_lab_volume_lag.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 03` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: LAG for period-over-period change (5 min).
- [ ] `debug-04` **Debugging 04: encounter volumes jumped (merge fan-out)** · 12 min @2026-10-14
  Start: read `03_python/debugging/04_site_merge_fanout/prompt.md` and say what you suspect.
  Done when: `python tasks.py test debugging 04` passes. That ticks it.
  New to this? `00_plan/background.md`: How merges multiply rows when keys repeat (4 min).
- [ ] `sql-04` **SQL 04: ED visits, running total and 7-day rolling average** · 20 min @2026-10-14
  Start: open `02_sql/problems/04_ed_running_total_rolling_avg.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 04` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Window frames, and Date spines with generate_series (9 min).
- [ ] `screen-tests` **Screen rebuild: three tests** · 20 min @2026-10-14
  Start: write test 1 (a code with whitespace and lowercase still maps) in `03_python/screen_rebuild/tests/`.
  Done when: `python tasks.py test screen` passes.
  New to this? `00_plan/background.md`: Writing small pytest tests (6 min).
- [ ] `sql-07` **SQL 07: gaps and islands, continuous enrollment** · 25 min @2026-10-14
  Start: open `02_sql/problems/07_continuous_enrollment_islands.md` and draw three overlapping periods on paper.
  Done when: `python tasks.py check-sql 07` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Gaps and islands (6 min).
- [ ] `lc-56` **LeetCode 56: merge intervals** · 20 min @2026-10-14
  Overlapping enrollment periods, in Python: sort by start, then extend or append. Compare SQL 07.
  Start: open https://leetcode.com/problems/merge-intervals/ and merge [[1,3],[2,6],[8,10],[10,12]] by hand first.
  Done when: Accepted on LeetCode. Then `python tasks.py done lc-56`.
  New to this? `00_plan/background.md`: Sorting with a key (6 min).
- [ ] `sql-06` **SQL 06: sites missing a quarterly submission** · 20 min @2026-10-14
  Start: open `02_sql/problems/06_missing_quarterly_submissions.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 06` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Date spines, Anti-joins, and Unpivot and LATERAL (13 min).
- [ ] `lc-py-windows` **LeetCode 929 and 1604: normalize codes, then a one-hour window** · 20 min @2026-10-14
  929 Unique Email Addresses (clean each string to a canonical form, then count a set), then 1604 Alert Using Same
  Key-Card Three or More Times in a One Hour Period (group times per name, sort, compare `times[i]` with `times[i-2]`).
  Start: open https://leetcode.com/problems/unique-email-addresses/ and normalize the first example email by hand.
  Done when: both Accepted on LeetCode. Then `python tasks.py done`.
  New to this? `00_plan/background.md`: Sorting with a key (6 min).
- [ ] `debug-02` **Debugging 02: baseline HbA1c missing or stale** · 12 min @2026-10-14
  Start: read `03_python/debugging/02_baseline_lab_window/prompt.md` and say what you suspect.
  Done when: `python tasks.py test debugging 02` passes. That ticks it.
  New to this? `00_plan/background.md`: Calendar dates vs. timestamps (6 min).

## Thu Oct 15 morning: warm-up set, done by 11:30

Interviews at 1:00 and 2:15. These are warm, not new: patterns from tonight, plus the perf answer you'll say out loud.
At 11:30, stop even with blocks left. Eat, walk, and open Google Meet at 12:45.

- [ ] `sql-slow-query` **Your answer to "how would you speed up a slow query?"** · 10 min @2026-10-15
  Start: scroll to the end of `02_sql/perf_lab.sql` and write the first sentence (when an index helps) from memory.
  Done when: three sentences written (when an index helps, when it doesn't, how you read a plan), said out loud once.
  New to this? `00_plan/background.md`: Reading EXPLAIN plans (13 min).
- [ ] `lc-sql-asof` **LeetCode 1164 and 550: value as of a date, then next-day retention** · 20 min @2026-10-15
  1164 Product Price at a Given Date (latest change on or before a date, with a default when there's none), then 550
  Game Play Analysis IV (first login per player, then check for a login the day after).
  Start: open https://leetcode.com/problems/product-price-at-a-given-date/ and say what a product with no change on or
  before 2019-08-16 gets.
  Done when: both Accepted on LeetCode. Then `python tasks.py done`.
  New to this? `00_plan/background.md`: Latest version per key (4 min).
- [ ] `sql-01` **SQL 01: latest HbA1c per patient, keeping ties** · 15 min @2026-10-15
  Start: open `02_sql/problems/01_latest_hba1c_with_ties.md` and read only Task and Output columns.
  Done when: `python tasks.py check-sql 01` prints PASS. That ticks it.
  New to this? `00_plan/background.md`: Ranking window functions (8 min).
- [ ] `lc-981` **LeetCode 981: time-based key-value store** · 20 min @2026-10-15
  The "as of" lookup in Python: a dict of sorted lists, then `bisect_right`. Compare LeetCode 1164 from the block above.
  Start: open https://leetcode.com/problems/time-based-key-value-store/ and say what `get` returns before the first set.
  Done when: Accepted on LeetCode. Then `python tasks.py done lc-981`.
  New to this? `00_plan/background.md`: Binary search with bisect (3 min).
- [ ] `debug-07` **Debugging 07: on time per the site, late per the audit log** · 12 min @2026-10-15
  Start: read `03_python/debugging/07_sftp_sla_timezone/prompt.md` and say what you suspect.
  Done when: `python tasks.py test debugging 07` passes. That ticks it.
  New to this? `00_plan/background.md`: Time zones: aware vs. naive datetimes (6 min).
- [ ] `lc-dry-run` **Dry run: one new problem, out loud, at interview pace** · 25 min @2026-10-15
  LeetCode 811 Subdomain Visit Count. Talk the whole time: restate it, ask one clarifying question, work one example by
  hand, name the edge cases, code it, then run your own test input before you submit.
  Start: open https://leetcode.com/problems/subdomain-visit-count/, run `python tasks.py timer`, restate it out loud.
  Done when: Accepted, or 25 minutes used. Then `python tasks.py done` and stop for the morning.

## Thu Oct 15 after 3:15: before Friday's design round

Only after both interviews. Design 02 and its background are here because Friday's interviewer likely builds this
kind of pipeline.

- [ ] `notes-pipeline-bg` **Before design 02: chunking notes and cutting LLM cost** · 20 min @2026-10-15
  Start: open `00_plan/background.md` and find "Chunking long notes: section-aware splits, overlap and provenance".
  Done when: both sections (chunking, then cutting LLM cost) watched or read, and their Check yourself answered out loud.
- [ ] `design-02` **Design 02: LLM extraction from clinical notes, speed round** · 20 min @2026-10-15
  Start: open `04_system_design/prompts/02_llm_note_extraction.md`, run `python tasks.py timer`, say the opener aloud.
  Done when: every section sketched on paper while talking, or time's up.
  New to this? `00_plan/background.md`: Calling an LLM at batch scale, and Evaluating extraction (13 min).
- [ ] `design-02-grade` **Grade design 02** · 10 min @2026-10-15
  Start: open `04_system_design/rubric.md` next to your paper.
  Done when: one row added to the Score log. Compare its weakest section with design 05's from the mock.
- [ ] `mpp-followups` **Warehouse-scale follow-ups: distribution and partitioning** · 15 min @2026-10-15
  Start: open `00_plan/background.md` and find "MPP distribution: hash keys, skew, and join data movement".
  Done when: both MPP sections' Check yourself answered out loud, then in two sentences, how you'd distribute and
  partition the extracted-facts table from design 02.

## Leftovers

Blocks you finished at about 65% land here as 10-minute blocks.

## Bonus

Only once Core is done, or as a change of pace.

- [ ] `screen-stdlib` **Screen rebuild with only the standard library, streaming** · 25 min
  Start: copy `standardize.py` to `standardize_stdlib.py` and swap the pandas read for `csv.reader`.
  Done when: same counts, then the same on `python tasks.py gen-data --big 5000000` with flat memory.
  New to this? `00_plan/background.md`: Generators, Streaming CSV, and Measuring peak memory (21 min).
- [ ] `sql-crawler-explain` **EXPLAIN on your job crawler's SQLite DB** · 20 min
  Needs the crawler's .db (none was in `..\Jobs` on Oct 11, so rerun the crawler first).
  Done when: one query goes from `SCAN` to `SEARCH ... USING INDEX`, added as a 3-line example at the end of stories.md.
- [ ] `lc-601` **LeetCode 601: human traffic of stadium** · 20 min
  Consecutive-row islands in SQL. https://leetcode.com/problems/human-traffic-of-stadium/
  New to this? `00_plan/background.md`: Gaps and islands (6 min).
- [ ] `lc-721` **LeetCode 721: accounts merge** · 20 min
  Union-find. https://leetcode.com/problems/accounts-merge/
  New to this? `00_plan/background.md`: Union-find (8 min).
- [ ] `lc-1795` **LeetCode 1795: rearrange products table** · 20 min
  Unpivot; compare SQL 05 and 10. https://leetcode.com/problems/rearrange-products-table/
  New to this? `00_plan/background.md`: Unpivot and LATERAL (5 min).
