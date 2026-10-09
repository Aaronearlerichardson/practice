# 05. Data quality monitoring and alerting

**Timebox: 45 min (speed round: 20 min)**

> "Data quality problems keep getting found by data scientists weeks after the data landed. Design a data quality monitoring and alerting service for our pipelines."

<details><summary>Interviewer's answers to clarifying questions</summary>

- **What's monitored:** All layers (bronze, silver, gold) across ~50 sites, ~8 source tables per site, ~120 dbt models total.
- **Kinds of problems seen so far:** A site's lab volume dropped 60% (extract bug on their side); a column went 100% null; weights recorded in pounds labelled as kg; duplicate encounters; orphaned diagnoses with no matching encounter; a site didn't deliver at all and nobody noticed for a month.
- **Existing checks:** Some dbt tests (`not_null`, `unique`) exist but failures are ignored because they're noisy.
- **Who acts:** Data engineers fix pipeline problems; a site liaison contacts sites; clinical informaticists judge plausibility rules.
- **Latency:** Problems should be flagged within hours of a delivery being processed, before data reaches gold.
- **Alert channels:** Slack and email; paging only for pipeline outages, not data issues (assume).
- **History:** Want trends per site over quarters (fill rate over time, etc.).
- **Constraints:** The checks themselves must not expose PHI in alerts or dashboards.

</details>

<details><summary>Follow-up curveballs</summary>

1. Your volume check fires every quarter for a site that legitimately grew 30%. How do you stop the false alarms without missing real drops?
2. A clinician says "a hemoglobin of 25 g/dL is impossible." Another says it's rare but real. Who decides, and how is that encoded?
3. A check fails on silver. Should gold still build?
4. A new site onboards with no history. What baselines do you use?
5. The DQ service itself is down during a delivery. What happens?
6. The alert message includes a sample of failing rows. What's wrong with that?

</details>

## Must cover

- **Requirements (1):** check types, owners, latency, alert routing, PHI in alerts.
- **Scale (2):** number of checks x sites x tables; how many alerts per quarter is tolerable.
- **Architecture (3):** where checks run (Glue Data Quality, dbt tests, custom), results store, alert router, dashboard.
- **Storage (4):** DQ results as an Iceberg table (check, site, table, run, value, threshold, status).
- **Retrieval (5):** dashboards, trend queries, drill-down without PHI.
- **Preprocessing (6):** check categories: schema, completeness, keys, volume, plausibility, freshness.
- **Fault tolerance (7):** gate vs. warn, quarantine, DQ service failures fail closed or open.
- **Monitoring (8):** alert fatigue metrics, acknowledgement, ownership.
- **Trade-offs (9):** static thresholds vs. statistical baselines; block vs. warn; build vs. buy.
