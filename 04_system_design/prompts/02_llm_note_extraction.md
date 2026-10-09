# 02. LLM extraction from clinical notes

**Timebox: 45 min (speed round: 20 min)**

> "A lot of what matters clinically is only in the notes: things like ejection fraction, smoking status, or why a drug was stopped. Design a system that pulls structured fields out of clinical notes using LLMs, and tells us whether we can trust the results."

<details><summary>Interviewer's answers to clarifying questions</summary>

- **Volume:** About 40M notes on hand across all sites; ~5M new notes per quarter. Median note ~1,200 tokens; long ones (discharge summaries) 8k+.
- **Formats:** Notes arrive as text in a table, RTF, or HTML depending on the site. Some have section headers, many don't.
- **Fields:** Start with ~20 fields for a cardiology study (e.g. LVEF value and date, NYHA class, smoking status). New studies add new fields every few months.
- **Relevance:** For most fields, under 5% of notes contain anything relevant.
- **Budget:** Assume a hard cap of $20k per quarter for LLM inference. Treat prices as assumptions.
- **Model access:** LLMs via a HIPAA-eligible provider under a BAA (e.g. Amazon Bedrock). Notes can't go to a vendor without a BAA.
- **Latency:** Batch. Results within a week of notes arriving is fine.
- **Ground truth:** Clinicians annotate a sample. Two clinicians label independently (double-blind); a third adjudicates disagreements.
- **Accuracy bar:** Study team wants precision and recall above ~0.90 per field before results are used.
- **Existing pieces:** A search engine index over notes exists. Assume OpenSearch.

</details>

<details><summary>Follow-up curveballs</summary>

1. The model provider releases a new version and you want to switch. How do you know it's not worse?
2. Finance says the bill tripled last quarter. Where do you look first?
3. The two clinician annotators agree only 70% of the time on NYHA class. What does that mean for your system?
4. A note says "no history of smoking, but father smoked 2 packs a day." Your extractor says "current smoker." How does that get caught, and how do you stop it happening at scale?
5. A study team needs the same extraction rerun six months later and must get identical answers. Can you guarantee that?
6. The LLM occasionally returns invalid JSON or times out. What happens to those notes?

</details>

## Must cover

- **Requirements (1):** fields, accuracy bar, budget, BAA/PHI, latency.
- **Scale (2):** tokens per quarter, cost before and after filtering.
- **Architecture (3):** notes -> normalize -> index -> filter cascade -> LLM batch -> validate -> Iceberg.
- **Storage (4):** extraction results with provenance (note ID, span, model, prompt version).
- **Retrieval (5):** how studies query extracted fields; how reviewers see evidence spans.
- **Preprocessing (6):** reformatting, sectioning, the filter steps, chunking long notes.
- **Fault tolerance (7):** retries, invalid output handling, idempotent re-extraction keyed on note + prompt + model.
- **Monitoring (8):** cost per field, precision/recall vs. ground truth, drift.
- **Trade-offs (9):** recall vs. cost in filtering; large vs. small model; caching vs. freshness.
