# How would you speed up a slow query? (sql)

Date: 2026-10-15. Graded: Partially accepted (3 sentences written; out-loud unverified).

## Aaron's three sentences
1. Indexes help because they guarantee the search tree is ordered, so you can use a B-tree search.
2. They don't help when too many items match your query, because then the number of B-tree searches becomes too large.
3. The first thing you read in a plan is the type of scan it will do. A sequential scan or a bitmap index changes the type of scan.

## Still fuzzy (open items)
- Sentence 1 and 2 lack the leading-column / sargable rule (function on the column, skipped leading column). E6 prediction assumed skipping the leading column still gives a fast index scan; check against the EXPLAIN result.
- Sentence 3 names scan types but not the numbers to compare: estimated vs actual rows, cost, actual time, buffers. The scan node is "Bitmap Heap Scan" fed by a Bitmap Index Scan.
- Teach-back and "what clicked" not yet recorded.

## Memorize vs look up
- Memorize: sargable on leading column; low selectivity means seq scan wins; predict the plan, then EXPLAIN ANALYZE.
- Look up: exact EXPLAIN node names and flags.

## Where to use it
Interview question "how would you speed up a slow query?" (Pedestal, Oct 15-16).
