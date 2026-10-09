# 03. Late corrections and "as of" datasets

**Timebox: 45 min (speed round: 20 min)**

> "Sites sometimes send corrections months after the original data. Meanwhile, we're putting together a dataset that will support an FDA submission, and we have to be able to reproduce exactly what we analyzed. Design how we handle both."

<details><summary>Interviewer's answers to clarifying questions</summary>

- **Corrections:** About 5-10 correction files per quarter. A correction can update values (wrong unit), delete records (patient opted out, duplicate), or add records that were missed. Usually scoped to one site, one table, one or more past quarters.
- **How corrections arrive:** Same SFTP path, flagged by a filename convention (`_CORRECTION_`) and a manifest stating which quarter they replace. Assume some sites send a full replacement of the affected quarter; others send only changed rows with an operation column (I/U/D).
- **FDA dataset:** Built from gold tables at a "data cut" date. Must be reproducible years later (assume retention of 10+ years after submission).
- **Reproducibility meaning:** Rerunning the analysis on the frozen cut must give the same numbers. Also need to explain what changed between two cuts.
- **Auditors:** Want to know who changed what and when. Assume 21 CFR Part 11 expectations for audit trails apply.
- **Opt-outs:** If a patient withdraws consent, they must be removed from future datasets. Legal says already-submitted datasets are retained as-is (assume).
- **Volumes:** Gold tables total ~2 TB. Daily dbt builds of gold.
- **Users:** Biostatisticians who analyze the cut; regulatory team who documents it.

</details>

<details><summary>Follow-up curveballs</summary>

1. Your Iceberg maintenance job expires snapshots older than 7 days. What happens to the FDA cut?
2. A correction arrives the day after the data cut is frozen. Does it go into the cut?
3. A biostatistician asks: "Why did the count of patients on drug X go from 4,112 to 4,089 between cut 3 and cut 4?" How do you answer that in under an hour?
4. A patient's deletion request conflicts with keeping an exact historical copy. How do you reconcile?
5. The dbt model logic changed between cuts (a bug fix in the cohort definition). Is the old cut still reproducible?
6. Two corrections for the same site and table arrive out of order. What happens?

</details>

## Must cover

- **Requirements (1):** correction types, what "reproducible" means, retention, deletions vs. retention.
- **Scale (2):** correction volume, snapshot storage overhead.
- **Architecture (3):** correction intake -> apply -> rebuild -> freeze cut.
- **Storage (4):** Iceberg MERGE for corrections; snapshot IDs and tags; snapshot retention; SCD2/dbt snapshots for change history.
- **Retrieval (5):** time travel by tag; diffing two cuts.
- **Preprocessing (6):** validating corrections; ordering; I/U/D handling.
- **Fault tolerance (7):** idempotent correction application, rollback, write-audit-publish.
- **Monitoring (8):** audit log, change reports per cut.
- **Trade-offs (9):** time travel vs. physical copy; MERGE vs. replace partition; copy-on-write vs. merge-on-read.
