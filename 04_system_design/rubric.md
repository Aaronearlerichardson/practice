# System design self-grading rubric

Grade yourself right after each attempt, before opening the model answer. Then grade again after reading it. The gap between the two scores is what to study.

## Scoring guide (per section)

| Score | Meaning |
|---|---|
| 0 | Skipped, or wrong in a way an interviewer would notice. |
| 1 | Mentioned, but generic: no numbers, no named mechanism, or no trade-off. |
| 2 | Specific: a concrete choice, the mechanism named (e.g. "Iceberg MERGE INTO on site + encounter_id"), the alternative and why it lost. |

Nine sections x 2 = 18 points. Target: 14+ with no section at 0.

## Checklist by section

### 1. Requirements (6 min)
- [ ] Asked who the users are and what they do with the output
- [ ] Asked about input format, number of sources, and frequency
- [ ] Asked about freshness/latency SLA
- [ ] Asked about volume
- [ ] Asked whether data contains PHI and who may see it
- [ ] Asked about corrections, history, or reproducibility
- [ ] Wrote assumptions down and labeled them "assume"
- [ ] Stopped asking by minute 7

### 2. Scale estimates (3 min)
- [ ] Gave rows and bytes per delivery with arithmetic shown
- [ ] Gave a growth or retention number (e.g. 5 years of history)
- [ ] Said what the numbers imply ("small for S3; the hard part is correctness")

### 3. Architecture (6 min)
- [ ] Drew sources -> landing -> ingest -> storage -> transform -> serve
- [ ] Showed orchestration and the trigger (event or schedule)
- [ ] Showed where PHI is removed or restricted
- [ ] Walked one unit of work through end to end

### 4. Storage (5 min)
- [ ] Named format and table format (Parquet, Iceberg) and catalog
- [ ] Explained the layers and what each guarantees
- [ ] Chose a partitioning scheme tied to the query pattern
- [ ] Chose a write mode (append / MERGE / partition overwrite) and said why
- [ ] Covered encryption and PHI separation

### 5. Retrieval (4 min)
- [ ] Named the query engine and the access pattern
- [ ] Gave a latency target
- [ ] Covered access control (Lake Formation, de-identified views)
- [ ] Covered reproducible reads (snapshot or tag)

### 6. Preprocessing (5 min)
- [ ] Schema validation and drift handling
- [ ] Normalization (units, codes, dates)
- [ ] Deduplication key named
- [ ] Quality checks: fill rate, key constraints, medical plausibility
- [ ] Separated blocking checks from warnings

### 7. Fault tolerance (6 min)
- [ ] Retries with backoff, limited to transient errors
- [ ] Idempotency story (deterministic key, ledger, MERGE or partition overwrite)
- [ ] Quarantine with a reason and a notification
- [ ] Backfill/replay from immutable raw; rollback of a bad write
- [ ] Answered "what if the same file arrives twice?"

### 8. Monitoring (3 min)
- [ ] Pipeline health (failures, duration) with alerting
- [ ] Data health (row count deltas, fill rates, freshness per site)
- [ ] Audit/lineage for PHI access and outputs

### 9. Trade-offs (4 min)
- [ ] At least three explicit "chose A over B because C" statements
- [ ] Said when you would switch
- [ ] Gave a closing summary and named the biggest risk

## Red flags (each one costs you, even if the rest is good)

- [ ] Named tools (Glue, Kafka, Spark) before asking a single requirement question
- [ ] No numbers anywhere
- [ ] Never mentioned PHI, HIPAA, or access control
- [ ] No idempotency story ("we'd just rerun it")
- [ ] Bad data is silently dropped rather than quarantined
- [ ] Proposed streaming for quarterly batch data without justifying it
- [ ] Overwrote or mutated raw data
- [ ] Monologued for 10+ minutes without checking in with the interviewer
- [ ] Ran out of time before fault tolerance
- [ ] Answered a curveball by restarting the design instead of adapting it

Red flags hit: ___ (subtract 1 point each)

## Score log

| Date | Prompt | Time used | Section scores (1-9) | Red flags | Total /18 | Weakest section | Next action |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
