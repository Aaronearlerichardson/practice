# 01. Quarterly EHR ingestion

**Timebox: 45 min (speed round: 20 min)**

> "We partner with about 50 health systems. Every quarter each one sends us an extract of their EHR data. Design the system that takes those deliveries and turns them into clean tables our data scientists can use."

<details><summary>Interviewer's answers to clarifying questions</summary>

- **Delivery:** Sites upload to an SFTP endpoint backed by S3. Formats vary by site: CSV, TSV, or Parquet. Some sites gzip their CSVs.
- **Contents:** About 8 tables per site: patients, encounters, diagnoses, procedures, medications, labs, vitals, notes metadata. Each site uses its own column names and local codes.
- **Volume:** Sites range from 20k to 2M patients. A typical delivery is 2-10 GB uncompressed; the largest is ~60 GB. Total about 1 TB raw per quarter.
- **Full or incremental:** Most sites send a full refresh each quarter. About 10 send only changes since last quarter. Assume you can't easily tell which from the files alone; there is a site config.
- **Timing:** Deliveries trickle in over ~3 weeks after quarter end. Not all sites deliver every quarter.
- **SLA:** Silver tables for a site within 48 hours of its delivery. Gold refresh after all sites land or by a cutoff date.
- **Users:** About 15 internal data scientists query with SQL and Python notebooks.
- **PHI:** Raw data includes names, DOBs, MRNs, addresses. Data scientists should work on de-identified or limited data, not raw identifiers.
- **History:** Analysts sometimes need to know what a site's data looked like in a prior quarter.
- **Team:** 4 data engineers. Preference for managed AWS services.

</details>

<details><summary>Follow-up curveballs</summary>

1. A site renames `lab_result_value` to `result_val` and adds three columns without telling anyone. What happens?
2. A site uploads the same 40 GB file twice, two hours apart. Walk me through what your system does.
3. The Glue job for the largest site fails at 80% through writing silver. What state are the tables in, and how do you recover?
4. Site 17 tells us last quarter's medication data had a unit bug. They're sending a corrected file for that quarter only.
5. Leadership wants to add 150 more sites next year. What breaks first?
6. A data scientist says lab counts for one site dropped 40% this quarter. How would you have caught that before she did?

</details>

## Must cover

- **Requirements (1):** full vs. incremental deliveries, PHI access, 48 h SLA, history needs.
- **Scale (2):** ~1 TB raw/quarter, file counts, peak week throughput.
- **Architecture (3):** SFTP/S3 landing -> event trigger -> Step Functions -> Glue -> Iceberg -> dbt.
- **Storage (4):** raw/bronze/silver/gold, partitioning, write mode for full vs. incremental sites.
- **Retrieval (5):** Athena, Lake Formation, de-identified views.
- **Preprocessing (6):** per-site schema mapping, type casting, code mapping, DQ gates.
- **Fault tolerance (7):** idempotent re-delivery, atomic commits, quarantine, backfill of a corrected quarter.
- **Monitoring (8):** per-site delivery tracker, row count deltas.
- **Trade-offs (9):** MERGE vs. overwrite; per-site config vs. per-site code; block vs. warn.
