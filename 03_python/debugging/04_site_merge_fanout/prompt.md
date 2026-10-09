# 04. Encounter volumes jumped after the reference refresh

**Timebox: 12 min**

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

Fix `buggy.py` so the enriched table has exactly one row per encounter and
uses each site's current attributes. If the reference data is ever broken
(two current rows for one site), the job should fail loudly rather than
produce inflated numbers.

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
