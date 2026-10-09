# Block 1: Cross-functional stories (1.5 h)

Write five stories. Each one: about 2 minutes spoken, in situation, action, result order. Then tell each out loud once.

Rules:
- Only details you can defend under a follow-up question. If you don't remember a number, describe it without one.
- Your actions in first person ("I"), not "we."
- Every story ends with a result and one thing you'd do differently.
- The "Known facts" are only what you've said in this project. Fill everything else yourself.

---

## 1. Translating a need into a technical solution

**Likely questions:** "Tell me about a time you turned a vague request into a technical solution." / "How do you build for non-technical users?"

**Known facts:** Lab scientists weren't expert coders. You built the `ieeg` package: pip-installable, prebuilt wheels, documented, runs on Mac, Windows, Jupyter, and the cluster.

- Situation (who needed what, and what was broken before):
- Action (how you found out what they needed; the decisions you made):
- Result (who uses it now; what changed):
- Would do differently:

## 2. Driving a change people depended on

**Likely questions:** "Tell me about a change you led that others had to adopt." / "How do you handle resistance?"

**Known facts:** Migrated the lab from custom-header `.dat` binaries to BIDS (EDF plus JSON sidecars) while others kept running analyses.

- Situation:
- Action (how you kept existing work from breaking; how you got buy-in):
- Result:
- Would do differently:

## 3. Working with people outside your team

**Likely questions:** "Tell me about collaborating with an external team." / "A dependency broke your work. What did you do?"

**Known facts:** mne-bids regression caught on a local test run on a fresh Windows install (not by CI). Issue #1290, merged PR #1291; named contributor in mne-bids 0.16. Also issue #1398 / PR #1399 (April 2025).

- Situation:
- Action (how you diagnosed it; how you worked with the maintainers):
- Result:
- Would do differently (CI gap):

## 4. A trade-off under risk or constraint

**Likely questions:** "Tell me about a technical trade-off you made." / "How do you handle risk to data?"

**Known facts:** Data on Duke Box (HIPAA-compliant, unlimited storage); the lab didn't fully trust it, so data was also kept on an offsite server.

- Situation:
- Options you weighed:
- Action:
- Result:
- Would do differently:

## 5. Prioritization

**Likely questions:** "How do you prioritize competing requests?" / "Tell me about a time you had to say no."

**Known facts:** None yet. Candidate material: pipeline support requests from labmates vs. your own paper. Pick one real episode.

- Situation:
- How you decided (what criteria):
- Action (including what you communicated, and to whom):
- Result:
- Would do differently:

---

## Also have a short answer ready for

- "Tell me about a disagreement with a colleague or PI."
- "Tell me about a mistake you made." (The SLURM log-naming bug works: reruns overwrote records, so outputs couldn't be traced to runs; you found and fixed it.)
- "How would you explain a data-quality problem to a non-technical stakeholder?"
- "What do you do when requirements are unclear?"
