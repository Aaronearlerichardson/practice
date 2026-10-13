-- Block 2: Index and EXPLAIN lab (Postgres, about 45 min; then 3 problems)
-- Run in DataGrip against a scratch database. For each experiment:
--   1. Write your prediction in the comment BEFORE running.
--   2. Run EXPLAIN (ANALYZE, BUFFERS).
--   3. Note the plan node (Seq Scan / Index Scan / Bitmap Heap Scan / Index Only Scan) and execution time.

DROP TABLE IF EXISTS lab_events;
CREATE TABLE lab_events AS
SELECT g AS event_id,
       (random() * 50000)::int                                  AS patient_id,
       (ARRAY['ALT','AST','BILI','PLT','INR'])[1 + (random()*4)::int] AS test_code,
       round((random() * 200)::numeric, 1)                      AS result_value,
       timestamp '2024-01-01' + random() * interval '900 days'  AS collected_at,
       'S' || lpad((1 + (random()*11)::int)::text, 2, '0')      AS site_id
FROM generate_series(1, 2000000) g;
ANALYZE lab_events;

-- E1. Point lookup, no index.
-- Prediction: Seq Scan, because there is no index on patient_id, so Postgres will scan the entire table to find matching rows. it will be slow, especially with 2 million rows.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM lab_events WHERE patient_id = 12345;

-- E2. Same query after an index.
CREATE INDEX ix_lab_patient ON lab_events (patient_id);
-- Prediction: Index Scan, because there is an index on patient_id, so Postgres will use the index to find the matching rows. it will be fast.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM lab_events WHERE patient_id = 12345;

-- E3. Wrapping the indexed column in an expression.
-- Prediction: Seq Scan, patient_id + 0 is an expression, so Postgres cannot use the index on patient_id. it will be slow, similar to E1.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM lab_events WHERE patient_id + 0 = 12345;

-- E4. Low-selectivity filter. Does an index on test_code help when 1 in 5 rows match?
CREATE INDEX ix_lab_test ON lab_events (test_code);
-- Prediction: Index Scan, because there is an index on test_code, so Postgres will use the index to find the matching rows. However, since 1 in 5 rows match, it may still be slower than a Seq Scan even slower than E1 and E3.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM lab_events WHERE test_code = 'ALT';

-- E5. Function on a timestamp column vs. a range predicate.
CREATE INDEX ix_lab_collected ON lab_events (collected_at);
-- Prediction (function): seq scan, because date_trunc('day', collected_at) is a function, so Postgres cannot use the index on collected_at. it will be slow.
EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM lab_events WHERE date_trunc('day', collected_at) = '2025-03-15';
-- Prediction (range): index scan, because collected_at >= '2025-03-15' AND collected_at < '2025-03-16' is a range predicate, so Postgres can use the index on collected_at. it will be fast.
EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM lab_events
WHERE collected_at >= '2025-03-15' AND collected_at < '2025-03-16';

-- E6. Composite index column order.
CREATE INDEX ix_lab_site_time ON lab_events (site_id, collected_at);
-- Prediction (leading column used): index scan, because site_id is the leading column in the index, so Postgres can use the index to find the matching rows. it will be fast.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM lab_events WHERE site_id = 'S03' AND collected_at >= '2026-05-01';
-- Prediction (leading column skipped): index scan, because collected_at is the second column in the index, so Postgres can still use the index to find the matching rows. it will be fast.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM lab_events WHERE collected_at >= '2026-06-15';

-- E7. Covering index: can Postgres answer without touching the table?
CREATE INDEX ix_lab_patient_cover ON lab_events (patient_id) INCLUDE (result_value);
VACUUM ANALYZE lab_events;
-- Prediction: Index Only Scan, because the index contains all the information needed to answer the query, so Postgres can use the index without touching the table.
EXPLAIN (ANALYZE, BUFFERS) SELECT result_value FROM lab_events WHERE patient_id = 12345;

-- E8. Latest result per patient: window function vs. DISTINCT ON. Compare plans and times.
-- Prediction:
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM (
  SELECT *, row_number() OVER (PARTITION BY patient_id ORDER BY collected_at DESC) AS rn
  FROM lab_events) t
WHERE rn = 1;
EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT ON (patient_id) * FROM lab_events ORDER BY patient_id, collected_at DESC;

-- E9. Correlated subquery vs. join + aggregate: patients whose latest ALT is above 150.
-- Write both versions yourself, then compare their plans.

-- When done, write 3 sentences: when an index helps, when it doesn't, and how you read a plan.
-- That paragraph is your interview answer to "how would you speed up a slow query?"
-- Then: LeetCode 178, 184, 1158.
-- Cleanup when finished (left commented so running the whole file doesn't drop it):
-- DROP TABLE lab_events;
