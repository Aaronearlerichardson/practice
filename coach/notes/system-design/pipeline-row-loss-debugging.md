# Pipeline row-loss debugging (warm-up, 2026-10-16)

Scenario: dashboard shows 412 enrolled for Site 07, coordinator expects about 460, fine on Friday.

## Aaron's answer (his words, condensed)
- Compare this week's reading with Friday's reading for the prior week, to tell a changed past (server-side) from a changed present (client-side).
- Then count enrolled patients at each boundary: raw, ingestion and validation, Iceberg stage, gold table, to find where the number changes.
- Which logs to read depends on server vs client.

## What was solid
- Layer-by-layer counting and digging at the first layer where it changes.
- Checking whether history changed.

## Gaps to close
- Name the entity: distinct patients per site at every layer, including the source (EDC / S3), and first confirm the 460 is right.
- Likely causes in CLEAN: dedup key collapsing patients, filter on a renamed or recased value, failed cast to NULL, INNER JOIN to a lookup missing a new value.
- Fixes: quarantine table with a reason column, RAW-vs-CLEAN count reconciliation per site per run with alerts, tests.

## Behavioral warm-up (five-stories)
Both stories were good but missed the closing "what I'd do differently" and the impact on earlier work; setup ran long. Re-check Oct 19.

## Memorize vs look up
Memorize: count the same entity at every layer; first drop is where to dig; the four usual causes. Look up: specific log locations.

## Still fuzzy
Reflection questions (teach-back, what clicked) skipped for time before the 1:00 round.
