# 04. Pharma dataset delivery

**Timebox: 45 min (speed round: 20 min)**

> "We sell access to curated real-world datasets. A pharma customer subscribes to, say, a heart failure dataset and gets updates every quarter. Design how we deliver those datasets."

<details><summary>Interviewer's answers to clarifying questions</summary>

- **Customers:** About 12 pharma customers now, aiming for 40. Each subscribes to 1-5 datasets (disease areas).
- **Dataset size:** 50k-500k patients each; 20-200 GB per dataset version as Parquet.
- **Cadence:** Quarterly releases, plus occasional hotfix releases.
- **Delivery methods customers ask for:** Files to their S3 bucket, a Snowflake share, or (rarely) SFTP pull. Assume S3 is the most common.
- **De-identification:** Customers must receive de-identified data only. The company has used Safe Harbor so far but wants to keep more date detail. Assume an expert determination is possible.
- **Linkage:** Some customers want to link our data with their own claims data, using privacy-preserving tokens. Tokens must differ per customer.
- **Versioning:** Customers need to know exactly which version they have, what changed, and must be able to reproduce prior analyses.
- **Contracts:** Each contract limits which tables and columns a customer may receive, and some exclude certain sites.
- **Audit:** We must be able to prove what we sent to whom and when.

</details>

<details><summary>Follow-up curveballs</summary>

1. A customer finds a bug in v2025.3: a lab unit was wrong for one site. What do you ship and how do you tell them?
2. A site leaves the network and its data can no longer be distributed. What happens to future and past releases?
3. Two customers compare notes and could join their datasets on our token. Is that a problem? How did you prevent it?
4. A customer's S3 bucket policy changes and your delivery fails halfway through copying 150 GB. What happens?
5. A new customer wants exact dates of service, not shifted dates. How do you respond?
6. Release day: 40 customers x 3 datasets each. How long does it take, and what's the bottleneck?

</details>

## Must cover

- **Requirements (1):** delivery channels, de-id method, contract scoping, versioning, audit.
- **Scale (2):** total bytes per release across customers; build vs. copy cost.
- **Architecture (3):** gold -> dataset build -> de-id + tokenization -> per-customer package -> deliver -> manifest/audit.
- **Storage (4):** versioned dataset tables (Iceberg tags) vs. per-customer materialized copies.
- **Retrieval (5):** how customers access; release notes and diffs.
- **Preprocessing (6):** Safe Harbor vs. expert determination; date shifting; small-cell suppression; per-customer tokens.
- **Fault tolerance (7):** resumable, idempotent delivery; manifest with checksums; atomic "release complete" marker.
- **Monitoring (8):** delivery ledger, re-identification risk checks, customer-facing status.
- **Trade-offs (9):** share vs. copy; one build per customer vs. one build plus filtered views.
