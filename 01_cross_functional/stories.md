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
 In my old lab, the Cogan lab, they needed to convert their pre-processing pipeline into a more standardized version 
- **Action** (how I found out what they needed; the decisions I made):
  - For their own consistency, since I found there were many inconsistencies in their practice
  - compatibility with external entities, since there were more updated versions of external chunks of the pipeline they could not take advantage of
- **Result** (who uses it now; what changed):
 It is now on a version controlled Python package that is compatible with multiple versions of Python on any operating system. It is used by every single member of the lab daily. The code base is organized and has documentation with clear examples that are used in onboarding.
- **Would do differently:**
I would probably add in a official type checker, like PyRefly, so that bug traces are more obvious. And I would be more inquisitive about everyone's workflow. Many of the lab members use Jupyter Notebooks. And I didn't necessarily integrate that into the pipeline.

## 2. Driving a change people depended on

**Likely questions:** "Tell me about a change you led that others had to adopt." / "How do you handle resistance?"

- **Situation:** 
The lab that I was in was used to sharing code via Dropbox. So everyone kept a version of the code that they worked on and then simply copied it, pasted it to Dropbox. This obviously caused a ton of version conflict issues.
- **Action** (how I kept existing work from breaking; how I got buy-in):
  - Before porting over any of the code, I started a separate repository that was simply a collection of all of the Dropbox code. So that it could be dropped into anyone's previous workflow if they needed it. As a backup.
- **Result:**
 I was able to get new members to use the new system entirely. And allowed old members to use the old code repository if they needed to, and update it if they want.
- **Would do differently:**
In the future, I would be more aggressive about deleting the Dropbox code set once it was ported over entirely. I left it up for some years and people some of the older users tended to use it. This caused a bunch of issues later down the line with compatibility.

## 3. Working with people outside your team

**Likely questions:** "Tell me about collaborating with an external team." / "A dependency broke your work. What did you do?"

- **Situation:**
a change in the way that time zones were saved and read in the M&E bids library broke how the public code read our files. making them unreadable.
- **Action** (how I diagnosed it; how I worked with the maintainers):
  - I was testing the new updated version of the reader on our local data.
  - I tested old and new versions of the code and found where the break was.
- **Result:**
I sent a pull request to mnebids to fix the error. 
- **Would do differently** (the CI gap):
One thing I would do differently is next time I would add a test that would catch that kind of error.

## 4. A trade-off under risk or constraint

**Likely questions:** "Tell me about a technical trade-off you made." / "How do you handle risk to data?"

- **Situation:** patient data storage
- **Options I weighed:**
  - Duke's box system, which is rated for PHI and has unlimited storage (which we found suspicious)
  - Duke DCC server synced to a local server in our lab.
- **Action:** kept any data that could be labeled as PHI on box and synced de-identified data to the DCC server.
- **Result:** fast secure and stable access to de-identified data and secure storage of unstructured PHI.
- **Would do differently:**

## 5. Prioritization

**Likely questions:** "How do you prioritize competing requests?" / "Tell me about a time you had to say no."

- **Situation:** I had a user that wanted to integrate Seaborn with Python package for visualization. into the IEEG package
- **How I decided** (what criteria): While it would allow them to save repeated plotting patterns that they often used it would add a new dependency into the package that wasn't required in order to complete the pre-processing of data. I determined that I shouldn't add unnecessary dependencies if I didn't have to
- **Action** (including what I communicated, and to whom): I told him to instead create a his own repository on GitHub. for those handy visualizations to save and share and let others edit
- **Result:** He did not end up creating his own own repository. and simply kept his visualizations to himself.
- **Would do differently:** I would tell him to send me his visualizations so that I can publish the repository.

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
