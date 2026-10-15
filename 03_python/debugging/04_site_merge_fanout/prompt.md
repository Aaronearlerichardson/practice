# 04. Encounter volumes jumped after the reference refresh

**Timebox: 12 min** | Fix: `03_python/debugging/04_site_merge_fanout/buggy.py`

## Input

`enrich_encounters` and `volume_by_region` both take
`(encounters, site_reference)`, two pandas DataFrames.

Table: `encounters`

```text
+--------------+------+-----------------------------+
| Column Name  | Type | Notes                       |
+--------------+------+-----------------------------+
| encounter_id | str  | unique per row, e.g. 'E01'  |
| patient_id   | str  | e.g. 'P00001'               |
| site_id      | str  | e.g. 'S01'                  |
+--------------+------+-----------------------------+
```

One row per encounter in the quarter.

Table: `site_reference`

```text
+-------------+-------------+------------------------------------------------+
| Column Name | Type        | Notes                                          |
+-------------+-------------+------------------------------------------------+
| site_id     | str         | e.g. 'S02'                                     |
| site_name   | str         | e.g. 'Harbor Health'                           |
| region      | str         | e.g. 'Northeast'                               |
| ehr_vendor  | str         | e.g. 'Epic'                                    |
| valid_from  | date or str | first day of the period; not read by the fix   |
| valid_to    | date or str | last day of the period, missing while open;    |
|             |             | not read by the fix                            |
| is_current  | bool        | True on the site's current row                 |
+-------------+-------------+------------------------------------------------+
```

Maintained by the site-onboarding team. Since the 2026-07 refresh it is a
type-2 history table: one row per site per period, so one `site_id` can have
several rows. Exactly one row per `site_id` should have `is_current == True`.

`buggy.py` also has `load_site_reference(path)`, which reads the onboarding
team's CSV extract (the same seven columns) into this frame. `site_id` stays
text, `valid_from` and `valid_to` become `datetime64` (`NaT` when empty), and
`is_current` is `True` only when the text is `true` in any case. The tests
do not call it, and the fix does not need to change it.

## Ticket (from the RWE analytics lead)

> The Q3 volume-by-region report shows the South region at roughly 3x last
> quarter and the Northeast at 2x. Nothing changed at those sites; their raw
> encounter files are about the same size as Q2. The total row count of the
> enriched table is also bigger than the encounter file we received.
>
> The only change I know of: the site-onboarding team refreshed the
> `site_reference` table in July. They said they "added history" so we can see
> when a site changed EHR vendor or name.
>
> Also, the report still shows some Northeast encounters under **Cerner**,
> but Harbor Health (S02) moved to Epic in April.

## Task

**Goal:** fix `buggy.py` so that the enriched table has exactly one row per
encounter, carrying its site's current attributes, and so that broken
reference data (two current rows for one site) makes the job fail loudly
instead of inflating the counts.

The fixed code runs these steps. Steps 1-4 are
`enrich_encounters(encounters, site_reference)` and steps 5-7 are
`volume_by_region(encounters, site_reference)`.

1. **Keep the current reference rows.** From `site_reference`, keep only the
   rows with `is_current == True`, and only the columns `site_id`,
   `site_name`, `region` and `ehr_vendor`. A site's current row is its row
   with `is_current == True`. `valid_from` and `valid_to` are not used.
2. **Check one current row per site.** If any `site_id` has more than one
   step 1 row, raise `pandas.errors.MergeError` (a subclass of `ValueError`;
   any message).
3. **Attach the site attributes.** For each row of `encounters`, in order,
   add `site_name`, `region` and `ehr_vendor` from the step 1 row with the
   same `site_id`. The result has exactly `len(encounters)` rows, a new index
   0 to n-1, and the columns of `encounters` in their order followed by
   `site_name`, `region`, `ehr_vendor`.
4. **Reject unknown sites.** An encounter's site is unknown when its
   `site_id` has no step 1 row, so `site_name` comes back missing. That
   includes a site whose reference rows all have `is_current == False`. If
   any site is unknown, raise
   `ValueError("encounters reference unknown sites: [...]")`, listing each
   unknown `site_id` once, sorted ascending, for example
   `encounters reference unknown sites: ['S06', 'S99']`. Otherwise return
   the step 3 frame.
5. **Enrich.** Run `enrich_encounters(encounters, site_reference)`. Its
   errors from steps 2 and 4 pass through unchanged.
6. **Count per (`region`, `ehr_vendor`).** One output row per distinct
   (`region`, `ehr_vendor`) pair in the enriched frame. `n_encounters` is the
   number of enriched rows with that pair, and `n_patients` is the number of
   distinct `patient_id` values among them.
7. **Sort.** Sort by `region` ascending, then `ehr_vendor` ascending, with a
   new index 0 to k-1.

## Output

`enrich_encounters(encounters, site_reference)` returns a DataFrame, one row
per row of `encounters`, in the same order:

| column | dtype | notes |
|---|---|---|
| encounter_id | str | `encounters.encounter_id` |
| patient_id | str | `encounters.patient_id` |
| site_id | str | `encounters.site_id` |
| site_name | str | the site's current row (step 3) |
| region | str | the site's current row (step 3) |
| ehr_vendor | str | the site's current row (step 3) |

`volume_by_region(encounters, site_reference)` returns a DataFrame, one row
per (`region`, `ehr_vendor`), sorted by `region` then `ehr_vendor`:

| column | dtype | notes |
|---|---|---|
| region | str | enriched `region` |
| ehr_vendor | str | enriched `ehr_vendor` |
| n_encounters | int64 | number of enriched rows with this pair (step 6) |
| n_patients | int64 | distinct `patient_id` among those rows (step 6) |

So `n_encounters` summed over all rows equals `len(encounters)`.

## Example

Try it on your code (inputs editable): `python tasks.py try debugging 04`.

Input `site_reference`:

```text
+---------+------------------------+-----------+------------+------------+------------+------------+
| site_id | site_name              | region    | ehr_vendor | valid_from | valid_to   | is_current |
+---------+------------------------+-----------+------------+------------+------------+------------+
| S01     | Lakeside Medical       | Midwest   | Epic       | 2024-01-01 | NaN        | True       |
| S02     | Harbor Health          | Northeast | Cerner     | 2024-01-01 | 2026-03-31 | False      |
| S02     | Harbor Health          | Northeast | Epic       | 2026-04-01 | NaN        | True       |
| S03     | Valley Clinic          | South     | Athena     | 2023-06-01 | 2025-01-31 | False      |
| S03     | Valley Clinic Group    | South     | Athena     | 2025-02-01 | 2026-05-31 | False      |
| S03     | Valley Health Partners | South     | Athena     | 2026-06-01 | NaN        | True       |
| S04     | Mesa Regional          | West      | Epic       | 2024-01-01 | NaN        | True       |
| S05     | Desert Springs         | West      | Cerner     | 2025-01-01 | NaN        | True       |
| S06     | Old Mill Clinic        | Midwest   | Epic       | 2023-01-01 | 2025-12-31 | False      |
+---------+------------------------+-----------+------------+------------+------------+------------+
```

Input `encounters`:

```text
+--------------+------------+---------+
| encounter_id | patient_id | site_id |
+--------------+------------+---------+
| E01          | P1         | S01     |
| E02          | P2         | S02     |
| E03          | P2         | S02     |
| E04          | P3         | S03     |
| E05          | P4         | S03     |
| E06          | P3         | S03     |
| E07          | P5         | S04     |
| E08          | P6         | S05     |
+--------------+------------+---------+
```

<details><summary>The same input as Python, for a REPL</summary>

```python
import pandas as pd

site_reference = pd.DataFrame(
    [
        ("S01", "Lakeside Medical", "Midwest", "Epic", "2024-01-01", None, True),
        ("S02", "Harbor Health", "Northeast", "Cerner", "2024-01-01", "2026-03-31", False),
        ("S02", "Harbor Health", "Northeast", "Epic", "2026-04-01", None, True),
        ("S03", "Valley Clinic", "South", "Athena", "2023-06-01", "2025-01-31", False),
        ("S03", "Valley Clinic Group", "South", "Athena", "2025-02-01", "2026-05-31", False),
        ("S03", "Valley Health Partners", "South", "Athena", "2026-06-01", None, True),
        ("S04", "Mesa Regional", "West", "Epic", "2024-01-01", None, True),
        ("S05", "Desert Springs", "West", "Cerner", "2025-01-01", None, True),
        ("S06", "Old Mill Clinic", "Midwest", "Epic", "2023-01-01", "2025-12-31", False),
    ],
    columns=["site_id", "site_name", "region", "ehr_vendor",
             "valid_from", "valid_to", "is_current"],
)
encounters = pd.DataFrame({
    "encounter_id": ["E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08"],
    "patient_id":   ["P1",  "P2",  "P2",  "P3",  "P4",  "P3",  "P5",  "P6"],
    "site_id":      ["S01", "S02", "S02", "S03", "S03", "S03", "S04", "S05"],
})
```

</details>

Output of `enrich_encounters(encounters, site_reference)`:

```text
+--------------+------------+---------+------------------------+-----------+------------+
| encounter_id | patient_id | site_id | site_name              | region    | ehr_vendor |
+--------------+------------+---------+------------------------+-----------+------------+
| E01          | P1         | S01     | Lakeside Medical       | Midwest   | Epic       |
| E02          | P2         | S02     | Harbor Health          | Northeast | Epic       |
| E03          | P2         | S02     | Harbor Health          | Northeast | Epic       |
| E04          | P3         | S03     | Valley Health Partners | South     | Athena     |
| E05          | P4         | S03     | Valley Health Partners | South     | Athena     |
| E06          | P3         | S03     | Valley Health Partners | South     | Athena     |
| E07          | P5         | S04     | Mesa Regional          | West      | Epic       |
| E08          | P6         | S05     | Desert Springs         | West      | Cerner     |
+--------------+------------+---------+------------------------+-----------+------------+
```

Output of `volume_by_region(encounters, site_reference)`:

```text
+-----------+------------+--------------+------------+
| region    | ehr_vendor | n_encounters | n_patients |
+-----------+------------+--------------+------------+
| Midwest   | Epic       | 1            | 1          |
| Northeast | Epic       | 2            | 1          |
| South     | Athena     | 3            | 2          |
| West      | Cerner     | 1            | 1          |
| West      | Epic       | 1            | 1          |
+-----------+------------+--------------+------------+
```

The two error cases, as a REPL session:

```python
>>> bad_enc = encounters.copy()
>>> bad_enc.loc[0, "site_id"] = "S99"
>>> bad_enc.loc[1, "site_id"] = "S06"
>>> enrich_encounters(bad_enc, site_reference)
Traceback (most recent call last):
  ...
ValueError: encounters reference unknown sites: ['S06', 'S99']
>>> two_current = site_reference.copy()
>>> two_current.loc[two_current["site_id"] == "S03", "is_current"] = True
>>> enrich_encounters(encounters, two_current)
Traceback (most recent call last):
  ...
pandas.errors.MergeError: Merge keys are not unique in right dataset; not a many-to-one merge
...
```

The `MergeError` message can differ; the tests check only its type.

Explanation:

- **Step 1.** 6 of the 9 reference rows have `is_current == True`: one each
  for S01 to S05. S06 has no current row.
- **Step 2.** Each of S01 to S05 has exactly one current row, so nothing is
  raised. In `two_current`, S03 has three current rows, so `MergeError` is
  raised.
- **Step 3.** 8 encounters in, 8 rows out, in the same order. E02 and E03
  get S02's current vendor, Epic, not the old Cerner row. E04 to E06 get
  S03's current name, Valley Health Partners.
- **Step 4.** Every `site_id` in `encounters` has a current row. In
  `bad_enc`, S99 has no reference rows at all and S06 has only a row with
  `is_current == False`, so both are listed, sorted.
- **Step 5.** `volume_by_region` starts from the 8-row frame above.
- **Step 6.** Northeast/Epic has E02 and E03, both from P2: 2 encounters, 1
  patient. South/Athena has E04, E05, E06 from P3, P4, P3: 3 encounters, 2
  patients.
- **Step 7.** Midwest < Northeast < South < West. Inside West, Cerner comes
  before Epic. The counts add up to 8, the number of encounters.

## What you can change

- **Edit:** `buggy.py` only. Inside it, anything goes: function bodies,
  default values, new helper functions, imports.
- **Keep:** the names and parameters (names and order) of `enrich_encounters`
  and `volume_by_region`, because the tests import them.
- **Don't edit:** `test_04_site_merge_fanout.py`. The tests are the spec, so a
  pass only counts with them unchanged. To poke at the data, use a REPL or a
  scratch file.

## Run the tests

```powershell
python -m pytest 03_python\debugging\04_site_merge_fanout -q
```

<details><summary>Hints</summary>

1. Compare `len(encounters)` with `len(enriched)`. Then run
   `site_reference["site_id"].value_counts()`. What does a left join do when
   the right side has three rows for one key?
2. Which rows of the reference table do you actually want? And `merge` has a
   `validate=` argument that turns a silent fan-out into an exception.

</details>

## Say out loud

- Reproduce: the row count before vs after the join.
- Hypothesize: the key is not unique on the dimension side any more.
- Isolate: `value_counts()` on the join key; find the sites with more than one row.
- Fix: filter to current rows, and assert the join cardinality.
- Prevent: `validate="many_to_one"` on every dimension join, a uniqueness test
  on the reference table (dbt `unique` test on `site_id where is_current`), and
  a row-count reconciliation check before/after joins.
