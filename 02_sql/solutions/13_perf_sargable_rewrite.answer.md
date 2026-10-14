# PERF: rewrite a slow query and add an index: my answer

## 1. Diagnosis (before touching anything)
- The plan node doing the work:
- Rows scanned vs. rows returned:
- Why an index on test_code or collected_at can't help as written:

## 2. Fix
- Indexes added (and why this column order):
- Query changes:

## 3. Timing (paste the table from 13_perf_sargable_rewrite.report.md)

| Variant | Median ms | Speedup |
|---|---:|---:|
| slow query, no indexes | | 1.0x |
| your rewrite, no indexes | | |
| slow query + your indexes | | |
| your rewrite + your indexes | | |

## 4. Plan after
- New plan node(s):
- Buffers before -> after:

## 5. Interview answer (say it in 60 seconds)

## 6. Trade-offs and what I'd check in production
