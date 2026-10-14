# PERF: rewrite a correlated subquery: my answer

## 1. Diagnosis (before touching anything)
- The plan node doing the work:
- Rows scanned vs. rows returned:
- How many times each SubPlan runs (loops=), and why the runtime is loops x one full scan of labs:

## 2. Fix
- Indexes added (and why this column order):
- Query changes:

## 3. Timing (paste the table from 14_perf_correlated_subquery.report.md)

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
