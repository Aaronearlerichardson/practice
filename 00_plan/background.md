# Background

Short videos and readings for the ideas behind each problem. They're optional. Use one when a problem's topic is
new to you, before you start its clock. Each block in `queue.md` names the section it needs, so `python tasks.py next`
shows it.

**How to use a section:**

1. Watch the clip **or** do the reading. You don't need both.
2. Close it and answer **Check yourself** out loud. If you can't, go back to just the part you missed.
3. Leave **After you've tried** alone until you've attempted the problem. Some of those links come close to an answer.

None of this covers the mock problems (SQL 11 and 12, debugging 08, data task 04, design 05).

A video marked "(transcript not checked)" was confirmed only by its title, length and chapter list. YouTube blocked the
transcript check partway through the research. Every other link was read or watched in transcript on Oct 12.

**Contents:** [SQL](#sql) · [Python debugging](#python-debugging) · [Python data tasks](#python-data-tasks) ·
[System design](#system-design) · [Bonus: LeetCode](#bonus-leetcode)

---

## SQL

### Ranking window functions: ROW_NUMBER, RANK, DENSE_RANK
For: `sql-01`, `sql-02` · about 8 min

- **Watch:** [SQL Window Functions | Clearly Explained](https://www.youtube.com/watch?v=rIcB4zMYMas), Maven Analytics, 0:00–7:28.
  Builds OVER (ORDER BY ...) step by step, compares the three ranking functions on a tie (3:35–4:30), adds PARTITION
  BY (5:15), then filters "top 3 per group" in an outer query (6:50).
- **Or read:** [Window Functions tutorial](https://www.postgresql.org/docs/16/tutorial-window.html), PostgreSQL 16
  docs, section 3.5: the rank() example, then the last part on filtering in a subquery and the WINDOW clause. Tied rows
  share a rank there, but the page doesn't point out the gap that follows.
- **Check yourself:** For scores 90, 85, 85, 80 (highest first), what do ROW_NUMBER, RANK and DENSE_RANK give each row?
  Why can't a window function go in WHERE?

### Reading EXPLAIN plans
For: `sql-slow-query`, `sql-13`, `sql-14` · about 13 min

- **Watch:** [Postgres Explain Explained](https://www.youtube.com/watch?v=P7EUFtjeAmI), Hussein Nasser, all 10 min. Seq
  Scan vs. Index Scan vs. Index Only Scan, and how to read cost, rows and width. **One error:** he calls the cost
  numbers milliseconds. They're arbitrary planner units, and only "actual time" under ANALYZE is in ms. For bitmap
  scans, add [Bitmap Index Scan in PostgreSQL](https://www.youtube.com/watch?v=ew49CGzwXgs), Dev Portal, 0:23–3:03.
- **Or read:** [Using EXPLAIN](https://www.postgresql.org/docs/16/using-explain.html), PostgreSQL 16 docs: 14.1.1, plus
  the `loops` paragraph in 14.1.2. Keep [Use The Index, Luke: PostgreSQL operations](https://use-the-index-luke.com/sql/explain-plan/postgresql/operations)
  open as a one-line-per-node cheat sheet.
- **Check yourself:** A node shows loops=2000. What do its "actual time" and "rows" numbers mean, and how do you get the
  total time spent in that node?

### Gaps and islands
For: `sql-07`, `lc-601` · about 6 min

- **Watch:** [How to find consecutive streaks in data using SQL window functions](https://www.youtube.com/watch?v=ejeGJHeKn-o),
  Data with Zach, 4:55–9:45. In Postgres: LAG compares each row with the one before, a CASE turns "something changed"
  into a 1, and a running SUM of those 1s makes a streak id you can group by. He gets the CASE backwards once and fixes
  it on camera around 7:45.
- **Or read:** [How to Find the Longest Consecutive Series of Events in SQL](https://blog.jooq.org/how-to-find-the-longest-consecutive-series-of-events-in-sql/),
  Lukas Eder (jOOQ blog), section "Generating groups for consecutive dates". This is a second technique, useful for LC
  601: subtracting ROW_NUMBER from a value that steps by 1 gives a key that stays constant within each run. The examples
  are SQL Server syntax.
- **Check yourself:** In the flag-and-running-sum method, what earns a row a 1, and why does a running SUM of the flags
  give every row in one island the same id?
- **After you've tried (optional):** [GAPS and ISLANDS in SQL Server](https://www.youtube.com/watch?v=ffNngUTqYBM), Bert
  Wagner, 1:13–3:50. It merges overlapping date ranges, but its flag compares each start with only the previous row's
  end, which breaks when one range sits inside a longer one. Build a 3-row case that it splits wrongly.

### Latest version per key (dedup)
For: `sql-08`, and its rule comes back in `sql-09` and `sql-10` · about 4 min

- **Watch:** [SQL: keep only the latest row per key, rerun-safe](https://www.youtube.com/watch?v=HykSStCPEi0), FDE
  Interviews, 0:00–2:23 (transcript not checked). ROW_NUMBER per business key, a unique tiebreaker so reruns keep the
  same survivor, and why GROUP BY + MAX on every column can build a row that never existed.
- **Or read:** [SELECT](https://www.postgresql.org/docs/16/sql-select.html#SQL-DISTINCT), PostgreSQL 16 docs, section
  "DISTINCT Clause" (the weather-reports example). This is the Postgres-only DISTINCT ON shortcut and its ORDER BY rule.
- **Check yourself:** If two versions tie on the timestamp, what makes ROW_NUMBER's pick repeatable? What must the ORDER
  BY look like for DISTINCT ON to work?

### Sargable filters and expression indexes
For: `sql-13` · about 6 min

- **Watch:** [7 Reasons PostgreSQL Ignores Your Index](https://www.youtube.com/watch?v=uFFr491XmK8), JaneExplainsIT,
  1:23–2:10, chapter "Functions and Type Casts" (transcript not checked).
- **Or read:** [Date and time conditions causing SQL performance problems](https://use-the-index-luke.com/sql/where-clause/obfuscation/dates),
  Use The Index, Luke, page "Date Types". Why a function on a date column hides it from the index, the explicit range
  rewrite, and the function-based-index alternative. Mostly Oracle examples. The Postgres ones are the quarter
  functions and the TO_CHAR example.
- **Check yourself:** Why can't a plain B-tree index on a timestamp column help a filter that wraps that column in a
  function? What are the two ways to make the filter index-friendly again?
- **After you've tried (optional):** [Indexes on Expressions](https://www.postgresql.org/docs/16/indexes-expressional.html),
  PostgreSQL 16 docs, 11.7. Short. Its last paragraph covers the write cost, which helps with the interviewer
  follow-ups.

### Multi-column index order
For: `sql-13` · about 6 min

- **Watch:** [The ESR (Equality, Sort, Range) Rule of Composite Indexes](https://www.youtube.com/watch?v=ficmoXWdhSU),
  Franck Pachot, PGConf India 2025, 0:00–2:38 (transcript not checked).
- **Or read:** [Indexing SQL range conditions](https://use-the-index-luke.com/sql/where-clause/searching-for-ranges/greater-less-between-tuning-sql-access-filter-predicates),
  Use The Index, Luke, section "Greater, Less and BETWEEN". Equality first, then range; access vs. filter predicates;
  and a note on reading Postgres's "Index Cond" line.
- **Check yourself:** With an equality filter on one column and a range filter on another, which goes first in a
  two-column B-tree index? What's the difference between an access predicate and a filter predicate?

### LAG for period-over-period change
For: `sql-03` · about 5 min

- **Watch:** [Lead & Lag Window Functions in SQL](https://www.youtube.com/watch?v=nHEEyX_yDvo), Ryan & Matt Data
  Science, 1:42–5:27 (transcript not checked). Basic LAG/LEAD, other offsets, and a default value for the empty first
  row. It's SQL Server, but the syntax is the same in Postgres.
- **Or read:** [Window Functions for Data Analysis with Postgres](https://www.crunchydata.com/blog/window-functions-for-data-analysis-with-postgres),
  Crunchy Data, section "Using date_trunc GROUP BY CTEs with Window Functions", then "LAG Analysis". **Skip** its "First
  and last values" example: it uses LAST_VALUE with the default frame, so its "last order" is really the current row.
- **Check yourself:** In which order does Postgres evaluate GROUP BY and window functions? What does LAG return on the
  first row of each partition?

### CTE steps, CASE, and VALUES lookup tables
For: `sql-09` · about 5 min

- **Watch:** [SQL CTEs (Common Table Expressions) - Why and How to Use Them](https://www.youtube.com/watch?v=ZaFMM-vNlvc),
  Database Star, 1:51–6:27 (transcript not checked). Turns a nested query into a CTE and why that reads better. MySQL
  sample data, same syntax in Postgres.
- **Or read:** [VALUES Lists](https://www.postgresql.org/docs/16/queries-values.html), PostgreSQL 16 docs, 7.7. A
  2-minute read: VALUES builds a constant table with named columns, usable anywhere a SELECT is.
- **Check yourself:** How do you give a VALUES list column names so you can join to it? Can a later CTE in the same
  WITH read from an earlier one?

### Conditional aggregation and pivot
For: `sql-10` · about 8 min

- **Watch:** [Using FILTER in SQL - EXPLAINING PostgreSQL](https://www.youtube.com/watch?v=5tQiYwEBNZw), CYBERTEC,
  0:00–10:19 (transcript not checked). Postgres's FILTER clause for partial aggregates.
- **Or read:** [Pivot — Rows to Columns](https://modern-sql.com/use-case/pivot), Markus Winand (Modern SQL), sections
  "Pivot — Rows to Columns" and "The Special Case of EAV". The FILTER and CASE forms, why NULL is the neutral value, and
  a mention of Postgres's crosstab.
- **Check yourself:** In a pivot, why do you still need an aggregate like max() when each cell holds only one value?
  What appears in a cell whose combination has no rows?

### Correlated subqueries vs. joins
For: `sql-14` · about 6 min

- **Watch:** [How to optimize correlated subqueries in Postgres](https://www.youtube.com/watch?v=UcI9TgCIOxQ), pganalyze
  ("5mins of Postgres" ep. 76), 0:00–6:10. Correlated vs. uncorrelated, scalar vs. tabular, why a correlated scalar
  subquery runs once per outer row, and IN vs. NOT IN. He says these run "as a nested loop". In your plan they show up
  as a SubPlan node with a high loops count, not as a Nested Loop node.
- **Or read:** [Subqueries and performance in PostgreSQL](https://www.cybertec-postgresql.com/en/subqueries-and-performance-in-postgresql/),
  Laurenz Albe (CYBERTEC), from "Correlated and uncorrelated subqueries" through "Scalar subqueries usually are a
  performance problem".
- **Check yourself:** Why does a correlated scalar subquery get slower as the outer row count grows, and which EXPLAIN
  ANALYZE field shows how many times it ran?
- **After you've tried (optional):** the same CYBERTEC article, section "Rewriting a scalar subquery in the SELECT list
  or WHERE clause".

### Window frames: running totals and rolling averages
For: `sql-04` · about 5 min

- **Watch:** [SQL window functions: rank, running totals and the ROWS vs RANGE trap](https://www.youtube.com/watch?v=-IOOF1FwSoM),
  FDE Interviews, 1:30–2:16. A running total where the default frame lumps tied dates together, and how ROWS changes
  that.
- **Or read:** [Window Function Calls](https://www.postgresql.org/docs/16/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS),
  PostgreSQL 16 docs, 4.2.8: only the frame_clause paragraphs, through the default-frame note. ROWS counts rows, RANGE
  measures distance in the ORDER BY value (an interval, for dates), and GROUPS counts peer groups.
- **Check yourself:** With only ORDER BY inside OVER, what frame do you get? How do "6 PRECEDING" under ROWS and
  "interval '6 days' PRECEDING" under RANGE differ when some dates are missing?

### Date spines with generate_series
For: `sql-04`, `sql-06` · about 4 min

- **Watch:** [Handling Missing Dates in SQL](https://www.youtube.com/watch?v=F_W2fdwbJZQ), Jeffrey James, 0:00–4:13
  (transcript not checked). Postgres generate_series as a calendar, with the data LEFT JOINed onto it.
- **Or read:** [Fill Gaps in Statistical Time Series Results](https://sqlfordevs.com/statistical-results-fill-gaps),
  Tobias Petry (SQL for Devs). Short. Read the Postgres generate_series version and skip the MySQL half.
- **Check yourself:** After a LEFT JOIN from a calendar, what do count(*) and count(a column from the data side) return
  on a day with no data, and why do they differ?

### Fill rates: NULLs, blanks and placeholders
For: `sql-05` · about 4 min

- **Watch:** [COUNT, DISTINCT, and NULLs in SQL Server](https://www.youtube.com/watch?v=p7PeZaP6Ku8), Bert Wagner,
  0:00–3:25 (transcript not checked). count(*), count(column) and count(DISTINCT column) when NULLs are present.
  Postgres follows the same rules.
- **Or read:** [FILTER — Selective Aggregates](https://modern-sql.com/feature/filter), Modern SQL, sections "Syntax" and
  "Conforming Alternatives". Counting only the rows that meet a condition, plus the CASE form.
- **Check yourself:** Which of count(*), count(col) and count(*) FILTER (WHERE ...) can treat an empty string as
  missing? How do you turn two counts into a percentage without integer division?

### Unpivot and LATERAL
For: `sql-05`, `sql-06`, `lc-1795` · about 5 min

- **Watch:** [Lateral Joins](https://www.youtube.com/watch?v=QQT8e9aewV0), PG Casts by Hashrocket, 0:00–4:17. Why a
  subquery in FROM can't see the outer row, and how LATERAL lets it (top 5 activities per developer).
- **Or read:** [How to Migrate Oracle's UNPIVOT to PostgreSQL](https://www.enterprisedb.com/postgres-tutorials/how-migrate-oracles-unpivot-postgresql),
  EDB, section "Replicating UNPIVOT in PostgreSQL". Two Postgres ways to turn columns into rows: unnest of arrays, and a
  LATERAL VALUES list.
- **Check yourself:** Why does a subquery in FROM need LATERAL to read columns from a table listed before it? When you
  unpivot with a VALUES list, do rows whose value is NULL disappear on their own?

### Anti-joins: NOT EXISTS vs. NOT IN
For: `sql-06` · about 4 min

- **Watch:** [The Query That Returned Nothing (NOT IN vs NOT EXISTS in SQL)](https://www.youtube.com/watch?v=IiNB0cw-1TE),
  Schoolhouse SQL, 0:52–4:56 (transcript not checked). One NULL in the subquery empties a NOT IN result, then three
  correct ways to write the anti-join.
- **Or read:** [Don't Do This](https://wiki.postgresql.org/wiki/Don%27t_Do_This#Don.27t_use_NOT_IN), PostgreSQL wiki,
  section "Don't use NOT IN". The NULL trap, and why Postgres can't turn NOT IN (subquery) into an anti-join.
- **Check yourself:** Why can `x NOT IN (subquery)` return zero rows when the subquery yields a NULL, and why doesn't NOT
  EXISTS have that problem?

---

## Python debugging

The three toolkit sections are for once, before your first debugging block. They apply to all seven exercises.

### Toolkit: run one test and read the failure
For: `debug-01` (once) · about 5 min

- **Watch:** [getting started with pytest](https://www.youtube.com/watch?v=mzlH8lp4ISA&t=260s), anthonywritescode,
  4:20–8:47. A pytest core developer shows how a plain `assert` failure prints both sides of the comparison, then `-v`
  to list test names and `-s` to show prints.
- **Or read:** [How to invoke pytest](https://docs.pytest.org/en/stable/how-to/usage.html#specifying-which-tests-to-run),
  section "Specifying which tests to run": `-k` keyword expressions and node IDs like `test_mod.py::test_func`.
- **Check yourself:** How do you run exactly one test, by node ID or with `-k`? When `assert a == b` fails, what does
  pytest print, and which value came from your code?

### Toolkit: pause inside the code with breakpoint()
For: `debug-01` (once) · about 10 min

- **Watch:** [python debugger crash course: pdb / breakpoint](https://www.youtube.com/watch?v=0LPuG825eAk&t=155s),
  anthonywritescode, 2:35–12:40. `breakpoint()`, then `l`/`ll`, `w`, `up`/`down`, `p`/`pp`, `n`, `s`, `r`, `c` and
  `q`, on a real codebase.
- **Or read:** [How to handle test failures](https://docs.pytest.org/en/stable/how-to/failures.html), sections
  "Stopping after the first (or N) failures" and "Using pdb with pytest": `-x`, `--pdb` (opens the debugger at the
  failure) and `breakpoint()` inside tests.
- **Check yourself:** What's the difference between putting `breakpoint()` in your code and running `pytest -x --pdb`?
  When would you pick each?

### Toolkit: shrink it to a minimal reproduction
For: `debug-01` (once) · about 3 min

- **Read:** [How to create a Minimal, Reproducible Example](https://stackoverflow.com/help/minimal-reproducible-example),
  Stack Overflow Help Center, sections "Minimal", "Complete" and "Reproducible". Its two shrinking strategies are
  "Restart from scratch" and "Divide and conquer". No video: this is shorter than any good one.
- **Check yourself:** What two ways does the page suggest for shrinking a failing program? How do you know the shrunk
  version still shows the same bug?

### Names, references and mutable objects
For: `debug-01` · about 10 min

- **Watch:** [Facts and Myths about Python names and values](https://www.youtube.com/watch?v=_AEJHKGk9ns&t=295s), Ned
  Batchelder (PyCon 2015), 4:55–10:30, then 15:38–19:31. The first clip covers why assignment never copies, mutable
  aliasing, and rebinding vs. mutating. The second shows that function arguments are just assignments (three versions of
  `append_twice`). **Stop at 19:31:** the Q&A after that is this section's "After you've tried".
- **Or read:** [Python Names and Values](https://nedbatchelder.com/text/names1.html), Ned's text version of the talk,
  from "Assignment never copies data" through "Three append_twice functions".
- **Check yourself:** After `a = [1]; b = a; b.append(2)`, what is `a`? How would you prove `a` and `b` are the same
  object, and how would you make `b` independent of `a`?
- **After you've tried (optional):** [the same talk, the audience question at 24:16](https://www.youtube.com/watch?v=_AEJHKGk9ns&t=1456s).
  A 45-second answer that explains the mechanism behind debug-01.

### Calendar dates vs. timestamps, and inclusive window edges
For: `debug-02` · about 6 min

- **Watch:** [Python Pandas Tutorial (Part 10): Working with Dates and Time Series Data](https://www.youtube.com/watch?v=UFuo7EHI8zc&t=889s),
  Corey Schafer, 14:49–20:49. Filters one year with `>=` its start and `<` the next start, compares against
  `pd.to_datetime(...)`, and shows date-string slices whose end covers the whole last day. **Outdated:** in pandas 2 and
  later, `df['2019']` raises KeyError. Use `df.loc['2019']`.
- **Or read:** [pandas user guide: Time series](https://pandas.pydata.org/docs/user_guide/timeseries.html#partial-string-indexing),
  "Partial string indexing" through "Slice vs. exact match". How pandas decides whether a date string means a whole day
  or one exact instant.
- **Check yourself:** Given timestamps that include times of day, how would you select every row on calendar days March
  1 to 31 inclusive? Is your upper bound closed or half-open, and why?
- **After you've tried (optional):** [pandas.Series.between](https://pandas.pydata.org/docs/reference/api/pandas.Series.between.html).
  Its `inclusive` parameter ("both", "left", "right", "neither") states each edge explicitly.

### How merges multiply rows when keys repeat
For: `debug-04`, `data-01-plan`, `screen-pandas` · about 4 min

- **Watch:** [Python Pandas For Your Grandpa - 3.7 DataFrame merge()](https://www.youtube.com/watch?v=oGGEI-X0CMs&t=29s),
  GormAnalysis, 0:29–3:53. Inner and left joins on a small pets/visits example. A key that appears twice on one side
  and three times on the other comes out as 6 rows.
- **Or read:** [pandas user guide: Merge, join, concatenate and compare](https://pandas.pydata.org/docs/user_guide/merging.html#merge-types),
  sections "Merge types", "Merge key uniqueness" and "Merge result indicator". Repeated keys on both sides give a
  Cartesian product, `validate=` raises `MergeError` when keys aren't unique, and `indicator=True` shows where each row
  came from.
- **Check yourself:** If the left table has 1 row for key K and the right table has 3, how many rows does a left merge
  return for K? Which `merge` argument makes pandas raise an error instead? What would a dict keyed on K hold?
- **After you've tried (optional):** [Kimball Group: Type 2 (slowly changing dimension)](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/).
  About 125 words on history rows, effective and expiry dates, and the current-row indicator. Useful vocabulary for the
  interview.

### Big-O: reading a timing curve
For: `debug-03` · about 8 min

- **Watch:** [Big-O: How Code Slows as Data Grows](https://www.youtube.com/watch?v=duvZ-2UK0fc&t=475s), Ned Batchelder
  (PyCon 2018), 7:55–16:27. Constant, linear and quadratic in plain words, how to count steps, and a worked example that
  turns out quadratic.
- **Or read:** [Big-O: How Code Slows as Data Grows](https://nedbatchelder.com/text/bigo.html), Ned's text version, from
  "Big-O" through "Another example".
- **Check yourself:** A function takes 1 s on 10k rows and about 4 s on 20k. What Big-O does that suggest, and what
  shape of code usually produces it?
- **After you've tried (optional):** [the same talk, "Python complexities"](https://www.youtube.com/watch?v=duvZ-2UK0fc&t=1087s),
  18:07–20:46. What common list, dict and set operations cost, and when converting from one to another pays off.

### Profiling: find the hot spot with cProfile
For: `debug-03`, `debug-05` · about 5 min

- **Watch:** [Diagnose slow Python code. (Feat. async/await)](https://www.youtube.com/watch?v=m_a0fN48Alw&t=39s),
  mCoding, 0:39–6:04. `with cProfile.Profile() as pr:`, sorting the stats by time, reading `tottime`, and the snakeviz
  icicle view. Stop at 6:04: the async fix that follows only applies to network code.
- **Or read:** [The Python Profilers](https://docs.python.org/3.14/library/profile.html#instant-user-s-manual), section
  "Instant User's Manual": `python -m cProfile -s`, sorting with `pstats`, and what `ncalls`, `tottime` and `cumtime`
  mean.
- **Check yourself:** What's the difference between `tottime` and `cumtime`? Which do you sort by to find the function
  whose own code is slow?

### Vectorizing pandas: whole-column operations instead of row loops
For: `debug-05` · about 8 min

- **Watch:** [Make Your Pandas Code Lightning Fast](https://www.youtube.com/watch?v=SAFmrTnEHLg&t=159s), Rob Mulla,
  2:39–10:23. One if/elif/else rule done three ways, with timings: an `iterrows` loop, `apply`, then boolean masks.
  Note that `apply(axis=1)`, his second version, still makes one Python call per row. Only the third is vectorized.
- **Or read:** [pandas user guide: Essential basic functionality](https://pandas.pydata.org/docs/user_guide/basics.html#iteration),
  section "Iteration", including `iterrows`. Why row iteration is slow, what to use instead, and why `iterrows` changes
  dtypes.
- **Check yourself:** How would you rewrite a per-row if/elif/else as whole-column boolean masks, while keeping the elif
  order (which rule wins) correct?
- **After you've tried (optional):** [numpy.select](https://numpy.org/doc/stable/reference/generated/numpy.select.html).
  Picks values from a list of conditions; when several are true, the first one wins.

### Memory: dtypes and processing in chunks
For: `debug-06` · about 5 min

- **Watch:** [Small Big Data: using NumPy and Pandas when your data doesn't fit in memory](https://www.youtube.com/watch?v=8pFnrr0NnwY&t=675s),
  Itamar Turner-Trauring (PyCon US 2020), 11:15–16:12. Smaller dtypes for the same data, then chunking: load a piece,
  compute, combine, move on, with `read_csv(chunksize=...)`.
- **Or read:** [pandas user guide: Scaling to large datasets](https://pandas.pydata.org/docs/user_guide/scale.html#use-efficient-datatypes),
  sections "Use efficient datatypes" and "Use chunking": `memory_usage(deep=True)`, category and downcast dtypes, and a
  `value_counts` built one file at a time.
- **Check yourself:** If a job only produces a small per-group summary, why shouldn't its memory grow with the file size?
  With chunked processing, what stays in memory between chunks?
- **After you've tried (optional):** [tracemalloc docs](https://docs.python.org/3.14/library/tracemalloc.html#record-the-current-and-peak-size-of-all-traced-memory-blocks),
  example "Record the current and peak size of all traced memory blocks". How peak memory is measured, so you can check
  your fix the same way.

### Time zones: aware vs. naive datetimes, converting to UTC
For: `debug-07` · about 6 min

- **Watch:** [MetPy Mondays #316 - Handling Time Zones in Python: A Practical Guide with zoneinfo](https://www.youtube.com/watch?v=kCY_-mnk60U&t=58s),
  NSF Unidata, 0:58–7:17. Starts from a naive local time, attaches a `ZoneInfo` zone, converts to UTC with
  `astimezone`, and does arithmetic between aware datetimes in different zones. Uses the standard-library `zoneinfo`,
  not `pytz`.
- **Or read:** [datetime docs](https://docs.python.org/3.14/library/datetime.html#aware-and-naive-objects), section
  "Aware and naive objects", then the `astimezone()` entry on the same page.
- **Check yourself:** Two aware datetimes show different clock times, but subtracting one from the other gives zero. How
  is that possible, and what single step makes comparisons like this safe?
- **After you've tried (optional):** [pandas user guide: Time zone handling](https://pandas.pydata.org/docs/user_guide/timeseries.html#time-zone-handling).
  `tz_localize` vs. `tz_convert`, and why `tz_localize(None)` and `tz_convert(None)` give different clock times.

---

## Python data tasks

### Stop pandas guessing types and NaNs
For: `data-01-plan` · about 4 min

- **Watch:** [Your CSV Reader is Wrong - Fix NaN Handling in Pandas](https://www.youtube.com/watch?v=r0TEuqsZpn8&t=100s),
  Data Automation, 1:40–5:00. How `na_values` and `keep_default_na` decide which text pandas turns into NaN. Recorded on
  pandas 2.0.3; the NA rules are the same in 3.0.
- **Or read:** [IO tools](https://pandas.pydata.org/docs/user_guide/io.html#na-values), sections "NA values" (the
  default list of strings that become NaN) and "Specifying column data types".
- **Check yourself:** With default `read_csv` settings, what happens to a value cell holding the text `NaN`, to an empty
  field, and to an id like `00042`?

### Parsing dates with a fixed format (strptime)
For: `data-01-plan` · about 3 min

- **Watch:** [Python Tutorial: Datetime Module](https://www.youtube.com/watch?v=eirjjyP2qcQ&t=1435s), Corey Schafer,
  23:55–26:35. Format codes, `strftime` (date to string) and `strptime` (string to date).
- **Or read:** [datetime docs](https://docs.python.org/3.14/library/datetime.html#format-codes), section "strftime() and
  strptime() format codes". Look at the rows for `%Y`, `%m` and `%d`.
- **Check yourself:** What does `datetime.strptime("2024-03-05", "%m/%d/%Y")` do?

The third section data task 01 needs is [How merges multiply rows when keys repeat](#how-merges-multiply-rows-when-keys-repeat),
under Python debugging.

### What makes a load idempotent
For: `data-02-plan` · about 4 min

- **Watch:** [The Importance of Idempotency in Designing Data Pipelines](https://www.youtube.com/watch?v=pKZ5n-y3ug4),
  PracticalGCP, 0:00–3:29. The definition (run once or 100 times, same result) and two examples: deduping to the latest
  record, and tracking which events were already processed.
- **Or read:** [How to make data pipelines idempotent](https://www.startdataengineering.com/post/why-how-idempotent-data-pipeline/),
  Start Data Engineering, sections "What is an idempotent function", "Why idempotency matters" and "Making your data
  pipeline idempotent". From 2021. Its delete-then-insert SQL isn't wrapped in a transaction, so a crash between the
  two steps would leave the data missing.
- **Check yourself:** In your own words, what's the difference between a job that's safe to rerun and one that isn't?
  Give one example of each from a pipeline you've built.
- **After you've tried (optional):** [Idempotent Data Load](https://www.youtube.com/watch?v=kXjI1NWI4M4&t=580s), The Data
  Channel, 9:40–12:30. INSERT OVERWRITE vs. MERGE/upsert as the two common idempotent write patterns. Rambling
  delivery, correct content.

### Transactions in sqlite3: all or nothing
For: `data-02` · about 2 min

- **Watch:** [Python SQLite Tutorial: Complete Overview](https://www.youtube.com/watch?v=pd-0G0MigUA&t=1430s), Corey
  Schafer, 23:50–25:35. `with conn:` commits when the block succeeds and rolls back when it raises. Stick to this
  range: around 11:30 he guesses that a SELECT auto-commits, which isn't true.
- **Or read:** [sqlite3 docs](https://docs.python.org/3.14/library/sqlite3.html#sqlite3-connection-context-manager),
  section "How to use the connection context manager". For more, "Transaction control" next.
- **Check yourself:** After an exception inside `with conn:`, what has happened to the rows inserted earlier in that
  block, and is `conn` still open?

### File checksums with hashlib
For: `data-02` · about 2 min

- **Read:** [hashlib docs](https://docs.python.org/3.14/library/hashlib.html#file-hashing), section "File hashing":
  `hashlib.file_digest` (added in 3.11). No video: this is shorter than any of them.
- **Check yourself:** Why must the file be opened in `"rb"` mode, and does the file's name affect the digest?

### Generators: one item at a time
For: `data-03-plan`, `screen-stdlib` · about 11 min

- **Watch:** [Python Tutorial: Generators](https://www.youtube.com/watch?v=bD05uGo_sVI), Corey Schafer, 0:00–10:50.
  `yield`, `next()`, StopIteration, generator expressions, and a 1M-record memory comparison against a list. It's
  Python 2: `xrange` is now `range`, and `time.clock()` was removed in 3.8. Two slips. At about 9:50, creating a
  generator runs none of its body, not "up to the first yield". And his memory comparison measures the generator before
  anything is read from it, so it overstates the gap. The real point holds: a for-loop over a generator keeps one item
  in memory at a time.
- **Or read:** [Python tutorial, 9.9 Generators and 9.10 Generator Expressions](https://docs.python.org/3.14/tutorial/classes.html#generators).
  About 330 words.
- **Check yourself:** While a for-loop runs over a generator that yields a million rows, how many rows are in memory at
  once? What changes if you wrap it in `list()`?

### Streaming CSV in and out with the csv module
For: `data-03-plan`, `screen-stdlib` · about 7 min

- **Watch:** [Python Tutorial: CSV Module](https://www.youtube.com/watch?v=q5uM4VKywbA&t=95s), Corey Schafer, 1:35–8:50.
  `csv.reader` as an iterator, `next()` to skip the header, `csv.writer`, and how the writer quotes fields that contain
  the delimiter. He opens files without `newline=''`. Always pass it: on Windows, `csv.writer` adds blank lines without
  it.
- **Or read:** [csv docs](https://docs.python.org/3.14/library/csv.html#csv.reader), the entries for `csv.reader` and
  `csv.writer`, plus footnote [1] on `newline=''`.
- **Check yourself:** Does creating a `csv.reader` read the file, or does reading happen as you loop? What type is every
  field it gives you?
- **After you've tried (optional):** [Accurately computing running variance](https://www.johndcook.com/blog/standard_deviation/),
  John D. Cook. Welford's one-pass mean and variance, and why the naive sum-of-squares formula loses precision. C++
  code, a 4-minute read.

### Measuring peak memory
For: `data-03`, `screen-stdlib` · about 3 min

- **Read:** [tracemalloc docs](https://docs.python.org/3.14/library/tracemalloc.html#tracemalloc.get_traced_memory), the
  entries for `start()`, `get_traced_memory()` and `reset_peak()`. No video: none short enough was correct.
- **Check yourself:** What do the two numbers from `get_traced_memory()` mean, and which one shows whether memory stayed
  flat across a 5M-row run?
- **After you've tried (optional):** [Measuring memory usage in Python: it's tricky!](https://pythonspeed.com/articles/measuring-memory-python/),
  Itamar Turner-Trauring. Resident memory (RSS) vs. allocated memory, and why what the OS reports can differ from what
  Python allocated.

### Exact vs. conflicting duplicates in pandas
For: `screen-pandas` · about 6 min

- **Watch:** [How do I find and remove duplicate rows in pandas?](https://www.youtube.com/watch?v=ht5buXUMqkQ&t=205s),
  Data School, 3:25–9:10. `duplicated()`, `keep='first'`/`'last'`/`False`, `drop_duplicates()` and `subset=`.
  Recorded in 2016; the API is the same in pandas 3.
- **Or read:** [pandas.DataFrame.duplicated](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.duplicated.html),
  the `subset` and `keep` parameters.
- **Check yourself:** Which rows does `duplicated()` mark with `keep='first'`, and which with `keep=False`?

### Writing small pytest tests
For: `screen-tests` · about 6 min

- **Watch:** [getting started with pytest](https://www.youtube.com/watch?v=mzlH8lp4ISA&t=180s), anthonywritescode,
  3:00–8:50 (the same video as the debugging toolkit, from a little earlier). File and function naming, plain `assert`
  and its failure messages, `pytest.approx`, `parametrize`, `-v` and `-s`.
- **Or read:** [pytest Get Started](https://docs.pytest.org/en/stable/getting-started.html#create-your-first-test),
  sections "Create your first test" and "Run multiple tests".
- **Check yourself:** What must a file name and a function name look like for pytest to collect them? Why is a function
  that takes rows and returns (good, rejects) easier to test than one that reads and writes files?

---

## System design

These sections run longer than the rest, and several prompts share them. Each design block's "New to this?" line
names the two or three to start with. The rest are for when you have time.

### How a data-engineering design interview runs
For: `design-template` · about 11 min

- **Watch:** [Data Engineering System Design Interview Framework](https://www.youtube.com/watch?v=ceClqzlmXaM), Data
  Guy, 2:20–13:30. Ask about the output side first (who uses it, how fresh, query pattern, retention), then the input
  side (source, schema, size). Then sketch a high-level design, check it with the interviewer, and go deep, ending with
  orchestration, validation and monitoring. That's the same order as your template. **Skip 4:15–5:30**: the CAP
  theorem aside is wrong. CAP is about a distributed store during a network partition and doesn't drive a batch
  pipeline's design.
- **Or read:** [How I Run System Design Interviews for Data Engineers](https://seattledataguy.substack.com/p/how-i-run-system-design-interviews),
  SeattleDataGuy's Newsletter (guest post by Mehdi Ouazza), sections "Wide & zoom through 3 core scenarios" and "What to
  look for". An interviewer on starting broad, zooming in, changing a requirement partway through, and what counts as
  depth versus breadth.
- **Check yourself:** Why pin down the output side (who reads the tables, how fresh, what queries) before the input
  side? What in prompt 01 would change if the consumer were a dashboard instead of 15 data scientists?

### Landing zone and raw / bronze / silver / gold layers
For: `design-01`, `design-03` · about 8 min

- **Watch:** [The Medallion Data Architecture (Pros & Cons)](https://www.youtube.com/watch?v=8p77fOWp5F4), Kahan Data
  Solutions, all 9 min (transcript not checked).
- **Or read:** [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion),
  Databricks docs, sections "Ingest raw data to the bronze layer", "Validate and deduplicate data in the silver layer"
  and "Power analytics with the gold layer". What each layer holds and how much checking belongs where. **One error:**
  it says the pattern "guarantees atomicity, consistency, isolation, and durability". ACID comes from the table format
  (Delta or Iceberg), not from the layering.
- **Check yourself:** Site 17 resends last quarter's medications with a unit fix. Which layers get rewritten, which
  stay untouched, and what lets you rebuild silver without asking the site to send anything again?

### Validation at the boundary: schema checks, quarantine, write-audit-publish
For: `design-01`, `design-03` · about 9 min

- **Watch:** [Building Reliable Data Pipelines with Apache Iceberg's Write–Audit–Publish Pattern](https://www.youtube.com/watch?v=kSrZI4LaqfA),
  Apache Iceberg Meetup, 1:40–10:25. Write to an isolated branch, audit, then publish in one atomic metadata step. Also
  a variant that splits bad records into a dead-letter table so good data isn't blocked. The speaker sells a
  data-quality product, and it turns into a pitch after about 12:00.
- **Or read:** [Data Quality Design Patterns](https://pipeline2insights.substack.com/p/data-quality-design-patterns-wap-awap),
  Erfan Hesami (Pipeline To Insights), sections "WAP (Write–Audit–Publish)" and "AWAP". AWAP adds an input audit before
  any transform (file format, columns present, types, row count). That's what checking at the boundary looks like.
- **Check yourself:** Name one check that should hold a site's whole delivery, and one that should only quarantine
  rows or raise a warning. What decides which bucket a check goes in?
- **After you've tried (optional):** [System Design for Senior Data Engineers: Building Pipelines That Scale](https://www.youtube.com/watch?v=Ha3nodOqHR0),
  The Data and AI Guy, 6:00–8:15. Data contracts that are checked by code and owned by a named person.

### Idempotent loads, re-deliveries and backfills
For: `design-01`, `design-03`, `design-04` · about 5 min

- **Watch:** [System Design for Senior Data Engineers: Building Pipelines That Scale](https://www.youtube.com/watch?v=Ha3nodOqHR0),
  The Data and AI Guy, 8:15–10:55. Every sink is idempotent on a stable key derived from the input, not a UUID made at
  write time. Backfills run through the same code as the forward path, in small ordered chunks. Monitor the data, not
  just the job.
- **Or read:** [How to make data pipelines idempotent](https://www.startdataengineering.com/post/why-how-idempotent-data-pipeline/),
  Start Data Engineering, sections "Why idempotency matters" and "Making your data pipeline idempotent" (the same
  article as data task 02's section, with the same caveat about its missing transaction).
- **Check yourself:** The same 40 GB file lands twice, two hours apart. What key tells your pipeline it has already
  processed this unit of work, and what exactly happens on the second arrival?
- **After you've tried (optional):** [Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html),
  Airflow docs, section "Creating a task" (about 2 min). The same idea in Airflow terms: treat a task like a database
  transaction, don't INSERT on a re-run, and read and write one specific partition.

### Retries and failure paths in the orchestrator
For: `design-01`, `design-02` · about 6 min

- **Watch:** [Step Functions Error Handling Mechanisms](https://www.youtube.com/watch?v=2nWzsBYRBEk), FooBar Serverless,
  2:40–8:15. Retry with interval, max attempts, backoff, max delay and jitter. Then Catch to a fallback state, and
  redrive to restart a failed execution from the step that failed.
- **Or read:** [Handling errors in Step Functions workflows](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html),
  AWS docs, sections "Retrying after an error" and "Fallback states". The fields your template names (ErrorEquals,
  IntervalSeconds, MaxAttempts, BackoffRate), and the order in which retriers and catchers are matched.
- **Check yourself:** In prompt 01, which two failures would you retry with backoff, and which two would you send
  straight to a Catch path? What makes the difference?

### Iceberg commits and write modes (MERGE vs. overwrite, copy-on-write vs. merge-on-read)
For: `design-01`, `design-03` · about 7 min

- **Watch:** [Apache Iceberg Tutorial: Copy-on-Write vs Merge-on-Read](https://www.youtube.com/watch?v=Vlw1R0HSHr0),
  Dremio, 0:00–3:20, then 7:50–9:45. Copy-on-write rewrites each touched file: slower writes, fast reads. Merge-on-read
  writes delete files: fast writes, but tables need compaction. The second clip covers when to pick each. Recorded in
  2022. Iceberg's v3 format later replaced position-delete files with deletion vectors, but the trade-off is the same.
- **Or read:** Iceberg docs, [Reliability](https://iceberg.apache.org/docs/latest/reliability/) (the whole page, about 3
  min: atomic commits, optimistic concurrency, retry on conflict). Then [Spark Writes](https://iceberg.apache.org/docs/latest/spark-writes/),
  sections "MERGE INTO" and "INSERT OVERWRITE" (dynamic vs. static overwrite).
- **Check yourself:** You have one full-refresh site and one changes-only site. Which write fits each (append, MERGE
  INTO, or dynamic INSERT OVERWRITE)? What does a reader see if the job dies 80% of the way through?

### Calling an LLM at batch scale: structured output and batch jobs
For: `design-02` · about 5 min

- **Watch:** [Get LLM to respond in JSON - OpenAI API Structured Outputs Explained](https://www.youtube.com/watch?v=JII7cloPjXc),
  Breakpoint, 6:48–10:40 (start at 0:25 if structured outputs are new to you). It extracts fields from a document into
  a typed schema and gets valid JSON with a wrong value in it. A schema guarantees the shape of the answer, not that
  it's true. The demo uses OpenAI; the idea is the same for Claude.
- **Or read:** [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), Claude
  docs, sections "Why use structured outputs" and "Important considerations" > "Invalid outputs" (a refusal or a
  max_tokens cutoff can still break the schema). Then the two notes at the top of Bedrock's
  [Process multiple prompts with batch inference](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html):
  batch jobs run on JSONL from S3 and don't support tool calling or structured output.
  [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) lists batch at 50% below on-demand for select models.
- **Check yourself:** Batch is half price but won't enforce a schema. Which notes go through batch and which through
  on-demand calls with structured output? What happens to a response that fails validation?
- **After you've tried (optional):** [Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/),
  Thinking Machines (Horace He): the intro, "Batch invariance and 'determinism'" and "How nondeterministic are
  completions?". Why temperature 0 still doesn't give identical reruns.

### Chunking long notes: section-aware splits, overlap and provenance
For: `notes-pipeline-bg` · about 9 min

- **Watch:** [The 5 Levels Of Text Splitting For Retrieval](https://www.youtube.com/watch?v=8OJC21T2SL4&t=640s), Greg
  Kamradt, 10:40–11:45, then 15:10–23:05. Chunk size and overlap shown visually, and each chunk keeping an ID and a
  pointer to its source document. Then recursive splitting that snaps to paragraph and word breaks, and splitting on
  Markdown headers, which is the same move as splitting a note on "HPI" or "Assessment and Plan". Recorded January 2024
  and aimed at retrieval. The library calls have changed since; the ideas haven't.
- **Or read:** [Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking), Unstructured docs,
  sections "Chunking Options", "'by_title' chunking strategy" and "Recovering Chunk Elements". A new section always
  closes the current chunk, overlap is opt-in, and each chunk keeps its original elements and their metadata. It's
  built for PDF and HTML, so for plain-text notes you'd detect the headers yourself. Then
  [Launching into clinical space with medspaCy](https://pmc.ncbi.nlm.nih.gov/articles/PMC8861690/), Eyre et al., AMIA
  2021, the "Section Detection" paragraph under Methods (about 1 min): rule-based matching of clinical section titles,
  and why the same phrase means something different under Past Medical History than in the current assessment.
- **Check yourself:** Why chunk a 9k-token discharge summary at all when the model accepts far more? If you do split it,
  what do you store with each extracted LVEF so a reviewer lands on the exact sentence, even when the same value turns
  up in two overlapping chunks?
- **After you've tried (optional):** [Introducing LangExtract](https://developers.googleblog.com/en/introducing-langextract-a-gemini-powered-information-extraction-library/),
  Google Developers Blog, section "What makes LangExtract effective for information extraction". An open-source
  extraction library that grew out of medical-extraction work. It maps every extracted value back to its exact
  character offsets in the source, and handles long notes with chunking, parallel calls and multiple passes.

### Cutting LLM cost: pre-filters, model cascades and prompt caching
For: `notes-pipeline-bg` · about 10 min

- **Watch:** [FrugalGPT: Reduce Cost and Improve Performance of Large Language Models](https://www.youtube.com/watch?v=pH7I32-VrZ0&t=568s),
  James Zou (Synthetic Intelligence Forum), 9:28–16:36. A FrugalGPT co-author covers five cost levers: shorter prompts,
  several questions in one call, caching answers, a fine-tuned small model, and a cascade where a cheap model answers
  first and a scoring function decides whether to escalate to a bigger one. Recorded June 2023, so the model names are
  old. His "caching" means reusing whole answers, which isn't prompt caching.
- **Or read:** [SPELL: regular expressions and LLMs for clinical information extraction](https://pmc.ncbi.nlm.nih.gov/articles/PMC13380079/),
  Kleinlein et al., 2026, sections "2.3 SPELL workflow" and "3.3 Retrieval coverage and recall audit". Regex finds
  candidate mentions, the LLM sees only ±100-character snippets around the hits, and notes with no hit never reach the
  LLM. It ran on 31M notes from 8 hospitals. Its recall audit of regex-negative notes was only 20 hand-picked notes
  per task, and its speed-up figures differ between sections.
- **Then, after either:** Bedrock's [Prompt caching for faster model inference](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html),
  sections "Types of prompt caching" and "Billing for cached tokens" (about 3 min). Read its note too: on Bedrock,
  caching works only on on-demand calls, not with batch inference. (Anthropic's own API does let caching and the batch
  discount stack, with cache hits best-effort.) Under "Getting started" > "Converse API", the last paragraph gives total
  input tokens as `inputTokens + cacheReadInputTokens + cacheWriteInputTokens`. Logging that per note gives you cost
  per note.
- **Check yourself:** A regex pre-filter sends 5% of 5M quarterly notes to the LLM. How would you find out how many true
  LVEF mentions it dropped? On Bedrock, would you run the survivors as a half-price batch job or on demand with a cached
  instruction prefix, and which numbers decide it?
- **After you've tried (optional):** [What is Prompt Caching?](https://www.youtube.com/watch?v=u57EnkQaUTY&t=365s), IBM
  Technology, 6:05–9:06. The cache matches from the first token and stops at the first difference, so fixed
  instructions and examples go first and the note goes last. Its "at least 1,024 tokens" and "cleared after 5 to 10
  minutes" are rough: on Bedrock, Claude minimums run from 512 to 4,096 tokens by model, and the cache lasts 5 minutes
  or 1 hour.

### Evaluating extraction: gold labels, precision and recall, human review
For: `design-02` · about 8 min

- **Watch:** [1. Introduction to LLM evaluations in 10 key ideas](https://www.youtube.com/watch?v=K8LLVi5Xrh8),
  Evidently AI, 3:27–8:00. Start with expert-labeled examples and evaluate against reference answers. Build test sets
  that include edge cases. An LLM judge is its own small model and needs its own evaluation. The examples are chatbots,
  but the ideas carry over.
- **Or read:** [Task-Specific LLM Evals that Do & Don't Work](https://eugeneyan.com/writing/evals/), Eugene Yan,
  sections "Classification/Extraction: ROC, PR, class distributions" and "Nonetheless, we still need human evaluation".
  Precision and recall per field, why accuracy misleads for rare fields, and aiming annotation at the cases the model is
  unsure about.
- **Check yourself:** A field appears in under 5% of notes and the bar is 0.90 precision and recall. How do you get
  enough labeled positives to measure recall for that field, and how do you rerun the check when the model version
  changes?
- **After you've tried (optional):** [Interrater reliability: the kappa statistic](https://pmc.ncbi.nlm.nih.gov/articles/PMC3900052/),
  McHugh 2012, sections "Percent agreement" and "Cohen's kappa". Why raw percent agreement overstates how much two
  annotators agree. The "% of data reliable" column in its Table 3 is the author's rule of thumb, not a standard.

### As-of history: two clocks (bitemporal)
For: `design-03`, `design-04` · about 8 min

- **Watch:** [Two Clocks: Bitemporal Facts and Backtest Bias](https://www.youtube.com/watch?v=zPd0_qCAMoM), TESSERACT
  ACADEMY ANIMATION, 0:00–2:20. Valid time vs. transaction time. A correction adds a row with a later recorded time, and
  SQL:2011 has a FOR SYSTEM_TIME AS OF clause. The examples come from finance.
- **Or read:** [Bitemporal History](https://martinfowler.com/articles/bitemporal-history.html), Martin Fowler: the
  opening, then "The Two Dimensions", "Changing the Retroactive Change" and "Append-only History". A salary gets
  corrected twice after payroll has already run. Actual history gets rewritten, but record history only grows.
- **Check yourself:** A site corrects a lab value in May for a draw in February, and the FDA cut was frozen in April.
  Write down the two dates on the corrected row, and say which one decides whether the April cut includes the
  correction.

### Change history with SCD Type 2 (dbt snapshots)
For: `design-03` · about 8 min

- **Watch:** [How to use dbt Snapshots to track data history](https://www.youtube.com/watch?v=SNtM_RUa5G4), Kahan Data
  Solutions, 0:43–9:20. Snapshot a source on a unique_key with the timestamp or check strategy, then read history
  through dbt_valid_from and dbt_valid_to. It uses the old Jinja `{% snapshot %}` syntax; dbt 1.9 and later configure
  snapshots in YAML, with the same ideas. **One error** at about 5:50: it describes check_cols as the way to identify a
  unique row. check_cols are the columns compared to detect a change; unique_key identifies the row.
- **Or read:** [Add snapshots to your DAG](https://docs.getdbt.com/docs/build/snapshots), dbt docs, sections "What are
  snapshots?" and "Detecting row changes" (including "Hard deletes"). The timestamp vs. check strategies, and the three
  ways to record rows deleted at the source.
- **Check yourself:** What do dbt_valid_from and dbt_valid_to mean when updated_at is the time a site's correction
  landed? What does a patient row the site deletes look like under each hard_deletes setting?

### Snapshots, tags and retention for frozen cuts and releases
For: `design-03`, `design-04` · about 7 min

- **Watch:** [Apache Iceberg data modifications, snapshots, and time travel](https://www.youtube.com/watch?v=kEd2HowSW-U),
  Starburst Academy, 0:49–7:45. Every write creates a snapshot, updates are logged as overwrites, and you can query an
  old snapshot by ID or roll the table back to it. **One error** at about 4:20: it says updates always create delete
  files. That's only merge-on-read, which Trino/Starburst uses. In copy-on-write mode, Iceberg rewrites the data file.
- **Or read:** [Branching and Tagging](https://iceberg.apache.org/docs/latest/branching/), Iceberg docs, sections
  "Overview", "Historical Tags" and "Audit Branch". Named tags have their own retention ("the default retention for
  branches and tags is forever"), and write-audit-publish can run on a branch.
- **Check yourself:** A maintenance job expires snapshots older than 7 days. What keeps the snapshot behind an FDA cut
  or a customer's v2025.3 alive? Besides the table data, what else would you need to rerun that analysis years later?
- **After you've tried (optional):** [Maintenance](https://iceberg.apache.org/docs/latest/maintenance/), Iceberg docs,
  section "Expire Snapshots" (about 1 min). What expiry removes from time travel, and when the data files actually get
  deleted.

### HIPAA de-identification: Safe Harbor vs. Expert Determination
For: `design-04` · about 10 min

- **Watch:** [HIPAA De-identification: Safe Harbor vs Expert Determination](https://www.youtube.com/watch?v=Dfdy7qAd5sw),
  Angel Reyes, 21:15–31:05. A worked Safe Harbor example where every date shrinks to the year and every ZIP to 3 digits.
  Then why Expert Determination exists, why passing Safe Harbor isn't automatically safe, why a limited data set is
  still PHI, and why "pseudonymized" isn't a legal status. For a side-by-side of the two methods, add 8:50–11:10.
- **Or read:** [Guidance Regarding Methods for De-identification of Protected Health Information](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html),
  HHS, sections 1.4 "The De-identification Standard" (skim the identifier list), 2.3 (what "very small" risk means), 2.5
  (several tailored datasets from one source), 2.9 (codes and keyed hashes) and 3.3 (which dates Safe Harbor forbids).
  This is the primary source. It blocked automated checks, so it was read from an Internet Archive copy dated Oct 5,
  2026; it should open normally in your browser.
- **Check yourself:** A new customer wants exact service dates. Under which method could you say yes, and who signs off
  based on what evidence? How does that change what the per-customer token is allowed to be?

### Delivering releases: share vs. copy
For: `design-04` · about 5 min

- **Watch:** [Snowflake Secure Data Sharing: Advantages, Limitations, and Best Practices](https://www.youtube.com/watch?v=PNbYMhJnwXM),
  SleekData, 0:22–3:00. A share is a metadata grant with nothing copied. The consumer pays for compute, gets read-only
  access and no Time Travel on shared objects, and can't re-share. One dated point: it says cross-region sharing needs
  manual replication. Snowflake now also offers listings with cross-cloud auto-fulfillment.
- **Or read:** [About Secure Data Sharing](https://docs.snowflake.com/en/user-guide/data-sharing-intro), Snowflake docs,
  sections "How does Secure Data Sharing work?", "What is a share?", "Reader accounts for third-party access" and
  "FAQs". Nothing is copied, the provider pays for storage and the consumer for compute, and a direct share works only
  within one region.
- **Check yourself:** One customer is on Snowflake in another region, and another wants Parquet in their own S3 bucket.
  What do you ship to each? How do you make a half-finished 150 GB copy safe to resume, and how do you later prove
  exactly what each customer received?

### MPP distribution: hash keys, skew, and join data movement
For: `mpp-followups` · about 6 min

The answer to "this query is slow on a 2-billion-row table" in a distributed warehouse goes past "add an index":
where do the rows live, and do they have to move to be joined?

- **Watch:** [Amazon Redshift: Distribution Styles & Data Skew](https://www.youtube.com/watch?v=dbn-g23iG2U&t=169s), Cram
  Exam, 2:49–5:25, then 7:04–7:53. The first clip covers the leader node and slices, the AUTO/KEY/EVEN/ALL styles, and a
  skew heat map. The second shows why two big tables on EVEN get shuffled at join time. Skip the Formula 1 storytelling
  around it. Then [Let's Learn Teradata Lesson 56: Table Size and Data Movement in a Join](https://www.youtube.com/watch?v=d5Xw9J03RQs&t=30s),
  Coffing Data Warehousing, 0:30–2:23, for the Teradata terms: a big table redistributed by the join key, or a small
  table duplicated to every AMP, with collected statistics deciding which. One overstatement: he says the optimizer
  "always uses the best plan". It picks the cheapest plan by its own estimates, which are only as good as the
  statistics.
- **Or read:** [Distribution styles](https://docs.aws.amazon.com/redshift/latest/dg/c_choosing_dist_sort.html), then
  [Choose the best distribution style](https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-best-dist-key.html),
  AWS Redshift docs, both whole pages (about 4 min). KEY, EVEN, ALL and AUTO; putting the fact table and one dimension
  on the same node; high cardinality after filtering; and when ALL is worth the extra storage. Teradata equivalents:
  primary index ≈ DISTKEY, AMP ≈ slice, duplicate ≈ broadcast.
- **Check yourself:** A 2-billion-row `lab_results` table is distributed on `test_status`, which has 4 values. It joins
  to a 40-million-row `encounters` table on `encounter_id`. What are the two separate problems with this design, and
  what would you look for in the query plan or the per-node row counts to confirm each?
- **After you've tried (optional):** [Evaluating the query plan](https://docs.aws.amazon.com/redshift/latest/dg/c_data_redistribution.html),
  AWS Redshift docs. The EXPLAIN labels (DS_DIST_NONE, DS_BCAST_INNER, DS_DIST_BOTH) that show whether a join had to
  move rows between nodes, which is the first thing to check on a slow join.

### Partitioning for pruning is a separate choice from distribution
For: `mpp-followups` · about 3 min

- **Watch:** [Let's Learn Teradata Lesson 27: Partitioning and the Row ID](https://www.youtube.com/watch?v=i-HVXlQLPuw),
  Coffing Data Warehousing, 0:00–2:23. The hash of the primary index (order number) picks the AMP. The partition (month
  of order date) then orders the rows inside each AMP, so a date filter can skip partitions on every AMP. From 2016,
  but this hasn't changed.
- **Or read:** [Single-AMP Queries and Partitioned Tables](https://docs.teradata.com/r/Lake-Database-Reference/Database-Design/Design-Issues-for-Tactical-Queries/Single-AMP-Queries-and-Partitioned-Tables),
  Teradata VantageCloud Lake docs, whole page (1 min). The partitioning key groups rows on each AMP and doesn't have to
  be part of the primary index. Then [Micro-partitions & Data Clustering](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions),
  Snowflake docs, sections "What are Micro-partitions?", "Query Pruning" and "What is Data Clustering?" (about 3 min).
  Snowflake has no distribution key for you to set; clustering is the only data-layout choice you control.
- **Check yourself:** Most queries on `lab_results` are either one patient's history or everything from the last 7
  days. Which column would you distribute on (or make the primary index), and which would you partition or cluster on?
  Why would distributing on `result_date` hurt the 7-day query?
- **After you've tried (optional):** [Sort keys](https://docs.aws.amazon.com/redshift/latest/dg/t_Sorting_data.html), AWS
  Redshift docs, the first three paragraphs. Redshift has no table partitions. It skips data with the sort key instead,
  using min and max values stored for each 1 MB block, and the sort key is chosen separately from the DISTKEY.

---

## Bonus: LeetCode

Concept material only, no walkthroughs of these exact problems. LC 601 uses [Gaps and islands](#gaps-and-islands) and
LC 1795 uses [Unpivot and LATERAL](#unpivot-and-lateral), both under SQL.

### Binary search with bisect
For: `lc-981` · about 3 min

- **Watch:** [Python Bisect Explained: Boundary Search, Duplicates, and Insertion Points](https://www.youtube.com/watch?v=4voHCLgwfbU),
  IFY Tools Interview Prep, 0:00–2:35. `bisect_left` vs. `bisect_right` on duplicates, and what an insertion point
  means. A new small channel; its claims match the docs.
- **Or read:** [bisect docs](https://docs.python.org/3.14/library/bisect.html#bisect.bisect_left), the entries for
  `bisect_left` and `bisect_right`, including the `key` parameter.
- **Check yourself:** For `a = [10, 20, 20, 30]`, what do `bisect_left(a, 20)` and `bisect_right(a, 20)` return? How
  does each index split the list?
- **After you've tried (optional):** [bisect docs, "Searching Sorted Lists"](https://docs.python.org/3.14/library/bisect.html#searching-sorted-lists).
  Five standard lookups built from the two functions.

### Sorting with a key
For: `lc-56` · about 6 min

- **Watch:** [Python Tutorial: Sorting Lists, Tuples, and Objects](https://www.youtube.com/watch?v=D3JvDWO-BY4&t=295s),
  Corey Schafer, 4:55–10:35. `key=` with `abs`, a custom function, a lambda, and `attrgetter`. The TypeError text he
  shows is from old Python 3; today it reads "'<' not supported between instances of ...".
- **Or read:** [Sorting Techniques](https://docs.python.org/3.14/howto/sorting.html#key-functions), sections "Key
  Functions" and "Sort Stability and Complex Sorts".
- **Check yourself:** What does `sorted()` do with `[[3, 4], [1, 9], [1, 2]]` by default, and how would you make it
  compare only the second number of each pair?

### Union-find (disjoint set union)
For: `lc-721` · about 8 min

- **Watch:** [Union Find - Union and Find Operations](https://www.youtube.com/watch?v=0jNmHPfA_yE), WilliamFiset,
  0:00–8:25. Parent pointers, find (follow parents to the root), union (point one root at the other), and merging the
  smaller group into the larger. He maps objects to array indexes first; in Python, a dict from item to parent does the
  same job.
- **Or read:** [Disjoint Set Union](https://cp-algorithms.com/data_structures/disjoint_set_union.html#naive-implementation),
  cp-algorithms, sections "Naive implementation", "Path compression optimization" and "Union by size / rank". C++ code;
  the prose takes about 3 min.
- **Check yourself:** After `union(a, b)` and `union(c, d)`, how many groups are there, and what do you compare to tell
  whether `a` and `d` are in the same group?
- **After you've tried (optional):** [Union Find Path Compression](https://www.youtube.com/watch?v=VHRhJWacxis),
  WilliamFiset, 0:00–6:35. How find becomes nearly constant time.
