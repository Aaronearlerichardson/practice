# Cross-functional stories

Five stories, about 2 minutes each when spoken. You wrote all five on Oct 9 and the reinstall deleted them.
This time, write them **from memory, as bullets**. Recalling them is the practice, so it will go faster than the
first draft. Bullets also keep you from memorizing a script that sounds read out.

**One story = one 15-minute block** (`python tasks.py next`):

1. Write the bullets from memory, about one line each. Don't scroll down or look anything up yet.
2. Check them against Known facts at the bottom of this file. Fix anything that's wrong, and cut any detail you couldn't defend under a follow-up.
3. Tell it out loud once on `python tasks.py timer 2`.

Rules:
- Only details you can defend under a follow-up question. If you don't remember a number, describe it without one.
- Your actions in first person ("I"), not "we."
- Every story ends with a result and one thing you'd do differently.

---

## 1. Translating a need into a technical solution

**Likely questions:** "Tell me about a time you turned a vague request into a technical solution." / "How do you build for non-technical users?"

- **Situation** (who needed what; what was broken before):
- **Action** (how I found out what they needed; the decisions I made):
  -
  -
- **Result** (who uses it now; what changed):
- **Would do differently:**

## 2. Driving a change people depended on

**Likely questions:** "Tell me about a change you led that others had to adopt." / "How do you handle resistance?"

- **Situation:**
- **Action** (how I kept existing work from breaking; how I got buy-in):
  -
  -
- **Result:**
- **Would do differently:**

## 3. Working with people outside your team

**Likely questions:** "Tell me about collaborating with an external team." / "A dependency broke your work. What did you do?"

- **Situation:**
- **Action** (how I diagnosed it; how I worked with the maintainers):
  -
  -
- **Result:**
- **Would do differently** (the CI gap):

## 4. A trade-off under risk or constraint

**Likely questions:** "Tell me about a technical trade-off you made." / "How do you handle risk to data?"

- **Situation:**
- **Options I weighed:**
- **Action:**
- **Result:**
- **Would do differently:**

## 5. Prioritization

**Likely questions:** "How do you prioritize competing requests?" / "Tell me about a time you had to say no."

- **Situation:**
- **How I decided** (what criteria):
- **Action** (including what I communicated, and to whom):
- **Result:**
- **Would do differently:**

---

## Short answers to have ready (one or two bullets each)

- "Tell me about a disagreement with a colleague or PI."
  -
- "Tell me about a mistake you made." (The SLURM log-naming bug works: reruns overwrote records, so outputs couldn't be traced to runs; you found and fixed it.)
  -
- "How would you explain a data-quality problem to a non-technical stakeholder?"
  -
- "What do you do when requirements are unclear?"
  -

---

## Known facts (check these after you write, not before)

**1. Translating a need into a technical solution.** Lab scientists weren't expert coders. You built the `ieeg` package: pip-installable, prebuilt wheels, documented, runs on Mac, Windows, Jupyter, and the cluster.

**2. Driving a change people depended on.** Migrated the lab from custom-header `.dat` binaries to BIDS (EDF plus JSON sidecars) while others kept running analyses.

**3. Working with people outside your team.** mne-bids regression caught on a local test run on a fresh Windows install (not by CI). Issue #1290, merged PR #1291; named contributor in mne-bids 0.16. Also issue #1398 / PR #1399 (April 2025).

**4. A trade-off under risk or constraint.** Data on Duke Box (HIPAA-compliant, unlimited storage); the lab didn't fully trust it, so data was also kept on an offsite server.

**5. Prioritization.** None yet. Candidate material: pipeline support requests from labmates vs. your own paper. Pick one real episode.
