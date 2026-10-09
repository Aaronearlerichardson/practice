# System design answer template

Use this skeleton for every prompt. It follows the order the interview is graded on: requirements, trade-offs, storage, retrieval, preprocessing, fault tolerance. Fill it in on paper or a whiteboard while you talk. Minute budgets assume a 45-minute interview; for 60 minutes, add the extra time to sections 3 to 7.

| # | Section | Minutes (45) | Cumulative |
|---|---|---|---|
| 0 | Opener | 1 | 1 |
| 1 | Requirements and clarifying questions | 6 | 7 |
| 2 | Scale estimates | 3 | 10 |
| 3 | Architecture | 6 | 16 |
| 4 | Storage | 5 | 21 |
| 5 | Retrieval | 4 | 25 |
| 6 | Preprocessing | 5 | 30 |
| 7 | Fault tolerance | 6 | 36 |
| 8 | Monitoring | 3 | 39 |
| 9 | Trade-offs and wrap-up | 4 | 43 |
| | Buffer for curveballs | 2 | 45 |

If you are past 10 minutes and haven't drawn a box, stop asking questions. Say "I'll assume X and move on" and write the assumption down.

---

## 0. Opener (first 60 seconds)

Say this nearly word for word:

> "Before I design anything, I want to make sure I'm solving the right problem. I'll spend a few minutes on requirements: who uses this, what goes in and out, how fresh it needs to be, and what the PHI constraints are. Then I'll do a rough size estimate, sketch the architecture end to end, and go deeper on storage, preprocessing, and what happens when things fail. I'll call out trade-offs as I go. Stop me anytime you want me to go deeper somewhere."

Then write four headings on the board: **Users / Inputs-Outputs / Freshness-Scale / Compliance**.

---

## 1. Requirements and clarifying questions (6 min)

**Functional** (what the system does)
- Who are the users? (Data scientists, clinicians, pharma customers, internal analysts, another system?)
- What are the inputs? Format, source, how many sources, push or pull?
- What are the outputs? Tables, files, API, dashboard? Who reads them and how?
- What operations matter: append only, updates, deletes, corrections?
- Is history needed? Do we need to reproduce what a table looked like on a past date?

**Non-functional** (how well it does it)
- Freshness / latency SLA: minutes, hours, days after arrival?
- Volume: rows, bytes, files per delivery; growth per year?
- Availability: what happens if this is down for a day?
- Correctness: is a wrong number worse than a late number? (In clinical evidence, almost always yes.)
- Cost sensitivity: is there a budget cap (e.g. LLM spend)?

**Compliance / PHI**
- Does the data contain PHI? Which of the 18 HIPAA identifiers?
- Who may see identified data vs. de-identified data?
- BAAs in place with the cloud vendor and any LLM vendor?
- Audit requirements: who accessed what, when? Retention period?
- Regulatory use (FDA submission) that requires reproducibility and audit trails?

Write the answers as a short list. Mark every guess with "assume."

**What you say out loud:** "So the core requirement is ___, the hard constraint is ___, and I'm going to optimize for correctness and auditability over latency unless you tell me otherwise."

---

## 2. Scale estimates (3 min)

Formula: **sources x records per source x bytes per record x frequency**, then compression and growth.

Worked mini example (50 sites, quarterly drops):
- 50 sites x 200k patients each = 10M patients.
- Per patient per quarter: about 30 lab rows, 5 encounters, 10 meds, 10 diagnoses = ~55 rows.
- 10M x 55 = 550M rows per quarter.
- ~200 bytes per row as CSV = ~110 GB raw CSV per quarter. Parquet with Snappy/ZSTD compresses roughly 5-10x, so ~15-20 GB stored per quarter.
- 5 years of history = 20 quarters x ~20 GB = ~400 GB. This is small for S3 and Iceberg. The hard part is correctness, not volume.
- Throughput: if all 50 sites land in the same week and we want processing within 24 h, that's ~110 GB/day. One Glue job with 10 DPUs handles that comfortably.

Prompting questions:
- Is the bottleneck bytes, row count, number of files, or number of sources?
- Is the load spiky (quarter end) or steady?
- What does it cost? (S3 standard ~$0.023/GB-month; Athena ~$5/TB scanned. Treat as approximate.)

**What you say out loud:** "Roughly ___ rows and ___ GB per ___. That's small enough that ___ isn't the problem; the hard part is ___."

---

## 3. Architecture (6 min)

Draw left to right: **Sources -> Landing -> Ingest/Validate -> Storage layers -> Transform -> Serve -> Consumers**, with **Orchestration** above and **Monitoring** below.

```
[sources] -> [landing S3] -> [ingest + validate] -> [raw/bronze Iceberg]
                                   |                        |
                             [quarantine]          [dbt: silver -> gold]
                                                            |
                                                  [serving: Athena/API/files]
      orchestration: Step Functions        monitoring: CloudWatch + DQ tables
```

Prompting questions:
- What triggers the pipeline: an event (S3 object created, EventBridge) or a schedule?
- Where is the boundary between "we stored exactly what we received" and "we changed it"?
- Where does PHI live, and where is it removed?
- What is the unit of work (one file, one site-quarter, one table)?

**What you say out loud:** "Let me walk one file through the system end to end, then I'll go deep on the pieces that matter most."

---

## 4. Storage (5 min)

- Format: Parquet files in an Iceberg table, Glue Data Catalog as the catalog.
- Layers: raw (byte-for-byte copy of what arrived) -> bronze (typed, one table per source table) -> silver (cleaned, conformed to a common model such as OMOP) -> gold (analysis-ready, use-case specific).
- Partitioning: by what column, and why? (Site and ingestion quarter are common; Iceberg hidden partitioning, e.g. `days(event_ts)` or `bucket(16, patient_id)`, means queries don't need to reference partition columns.)
- Write mode: append, MERGE INTO (upsert), or overwrite of a partition? Copy-on-write (fast reads, slower writes) vs. merge-on-read (fast writes, needs compaction)?
- History: Iceberg snapshots, tags for named versions, snapshot expiration policy.
- Encryption: SSE-KMS on S3; separate buckets/keys for PHI vs. de-identified data.
- Lifecycle: S3 lifecycle rules to move raw files to Glacier after N days.

**What you say out loud:** "I'm storing ___ in ___ partitioned by ___ because the main queries filter on ___. The alternative was ___, which I rejected because ___."

---

## 5. Retrieval (4 min)

- Who queries, how often, and with what pattern (scans, point lookups, aggregates)?
- Engine: Athena for ad hoc SQL; Redshift/warehouse for heavy BI concurrency; an API with a cache for an app; a search engine (OpenSearch) for text.
- Latency target: seconds for interactive, minutes OK for batch.
- Access control: Lake Formation table/column/row permissions; separate de-identified views.
- Reproducibility: can a consumer query "as of" a snapshot or tag?

**What you say out loud:** "Most reads are ___, so I'm optimizing the layout for ___. If someone needs ___, they'd use ___ instead."

---

## 6. Preprocessing (5 min)

- Schema validation: expected columns and types per site and table; schema drift handling.
- Type casting, date parsing, unit normalization (mg/dL vs mmol/L), code mapping (local lab codes -> LOINC, local drug codes -> RxNorm).
- Deduplication: on what key? Natural key + site, or a hash of the row?
- Patient identity: per-site IDs, tokenization for cross-site linkage.
- Quality checks as gates: fill rates, primary/foreign key constraints, medical plausibility (e.g. heart rate 0-300, birth date before encounter date).
- Where does it run: Glue (Spark) for heavy lifting at ingest, dbt for SQL transforms in the warehouse layers.

**What you say out loud:** "I separate checks that block the pipeline from checks that only warn. Blocking: ___. Warning: ___."

---

## 7. Fault tolerance (6 min)

Cover all four, in this order:

1. **Retries.** Step Functions `Retry` with `ErrorEquals`, `IntervalSeconds`, `MaxAttempts`, `BackoffRate`; `Catch` routes to a failure path. Retry only transient errors (throttling, timeouts), not bad data.
2. **Idempotency.** Running the same step twice gives the same result. Tools: a deterministic key per unit of work (site + quarter + file checksum), a manifest/ledger table recording processed files, MERGE on a natural key instead of blind append, overwrite of exactly one partition.
3. **Quarantine.** Bad files or rows go to a `quarantine/` prefix or table with the reason; the rest of the batch continues (or the whole site-quarter is held, depending on the rule). Someone gets notified.
4. **Backfill / replay.** Raw is immutable, so any downstream layer can be rebuilt from raw. Iceberg rollback to a previous snapshot if a bad write lands. dbt `--full-refresh` or targeted reruns for a site.

Prompting questions:
- What happens if the job dies halfway through writing?  (Iceberg commits are atomic: readers see the old snapshot or the new one, never half.)
- What if the same file arrives twice? What if a site resends a corrected file?
- What if two jobs write the same table at once? (Iceberg optimistic concurrency: one commit fails and retries.)

**What you say out loud:** "Every step is safe to rerun. If something fails, we retry transient errors, quarantine bad data with a reason, and because raw is immutable we can always rebuild downstream."

---

## 8. Monitoring (3 min)

- Pipeline health: Step Functions execution failures, duration, CloudWatch alarms -> SNS/Slack/PagerDuty.
- Data health: row counts vs. last quarter per site, fill rates, freshness (did site X deliver?), DQ test failures stored as a table.
- Lineage and audit: which snapshot produced which output; CloudTrail and S3 access logs for PHI access.
- Who gets paged vs. who gets a daily summary.

**What you say out loud:** "I monitor two things separately: is the pipeline running, and is the data right. The second is the one that bites in clinical data."

---

## 9. Trade-offs and wrap-up (4 min)

Name at least three, each as "I chose A over B because C; I'd switch if D."

| Decision | Chose | Alternative | Why | Would switch if |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

Common axes: batch vs. streaming; MERGE vs. overwrite; copy-on-write vs. merge-on-read; managed (Glue, Athena) vs. self-run (EMR, Spark on EKS); block-on-failure vs. warn; cost vs. latency; Safe Harbor vs. expert determination.

**Closing script (30 seconds):**

> "To summarize: data lands in S3 untouched, gets validated and written to Iceberg by an idempotent Step Functions workflow, and dbt builds silver and gold with tests as gates. Bad data is quarantined, not dropped, and every output is tied to a snapshot so it's reproducible. The biggest risk I see is ___, and if I had more time I'd go deeper on ___. What would you like me to dig into?"
