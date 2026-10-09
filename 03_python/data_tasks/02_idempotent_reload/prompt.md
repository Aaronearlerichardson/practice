# 02. The site resent Q1

**Timebox: 35 min**

Sites resend quarters. Sometimes the bytes are identical (someone re-ran the export), sometimes it's a real correction, and sometimes the new file is broken. The loader has to do the right thing every time, and a rerun must never double-count. Build it on `sqlite3` so the tests run anywhere. In production this would be Postgres or an Iceberg table, but the logic is the same.

## Inputs (`data/`)

| File | What it is |
|---|---|
| `s01_2024Q1.csv` | Site s01, Q1: 60 rows |
| `s01_2024Q1_resend.csv` | Byte-identical to the Q1 file, different name |
| `s01_2024Q1_corrected.csv` | 59 rows: three values corrected, two rows withdrawn, one late row added |
| `s01_2024Q1_broken.csv` | The corrected file with one bad row partway through |
| `s01_2024Q2.csv` | Site s01, Q2: 55 rows |
| `s02_2024Q1.csv` | Site s02, Q1: 40 rows |

Every file has the header `patient_id,test_code,collected_date,value,unit`. `python gen_data.py` regenerates them byte-identically.

## Schema (given in `solution.py` as `SCHEMA_SQL`)

- `lab_results(site_id, quarter, patient_id, test_code, collected_date, value REAL, unit)`
- `load_audit(load_id AUTOINCREMENT, site_id, quarter, file_name, checksum, row_count, status, message, loaded_at)`

`file_name` is the base name (`Path(path).name`), `checksum` is the SHA-256 hex digest of the file's bytes, and `loaded_at` is any timestamp you like (not tested).

## Rules for `load_quarter(conn, site_id, quarter, path)`

The **current version** of a site-quarter is the most recent audit row for that `(site_id, quarter)` whose status is `loaded` or `replaced`.

| # | Situation | Data effect | Audit row: `status`, `row_count` |
|---|---|---|---|
| 0 | `quarter` isn't `YYYYQ[1-4]` | none | **no row**: raise `ValueError` |
| 1 | Checksum equals the current version's checksum | none | `skipped`, 0 |
| 2 | Any line fails validation (below), or no data rows | none | `failed`, 0, message starts `line N:` for a bad line |
| 3 | Valid, and there's no current version | insert rows | `loaded`, rows inserted |
| 4 | Valid, and there is a current version | replace **only** this site-quarter's rows, atomically | `replaced`, rows inserted |
| 5 | A database error while writing in 3 or 4 | roll back everything, prior rows intact | `failed`, 0 |

Validation, with the header as line 1 and the first data row as line 2:

- The header must be exactly `patient_id,test_code,collected_date,value,unit`, with exactly 5 fields per row.
- `patient_id` and `test_code` are non-empty after trimming.
- `collected_date` is ISO `YYYY-MM-DD` and falls **inside the quarter**: start inclusive, end exclusive.
- `value` is a finite float.

Store fields trimmed, with `test_code` uppercased. The data change and its audit row are one transaction. A `failed` audit row must persist even though the data change was rolled back. Return with no transaction open.

## Implement (in `solution.py`)

```python
def init_db(conn) -> None
def file_checksum(path) -> str
def parse_quarter(quarter) -> tuple[date, date]               # (start, end_exclusive)
def read_and_validate(path, quarter) -> list[tuple[str, str, str, float, str]]
def load_quarter(conn, site_id, quarter, path) -> str          # loaded|replaced|skipped|failed
```

## Run the tests (PowerShell, from the repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest 03_python\data_tasks\02_idempotent_reload -q -p no:cacheprovider
```

<details><summary>Hints</summary>

- Validate the whole file into memory first, then touch the database. A quarter from one site is small, and you can talk through the streaming version.
- `with conn:` commits on success and rolls back on an exception. Put the DELETE, the INSERTs, and the success audit row inside one `with conn:` block.
- Write the `failed` audit row in its own transaction *after* the rollback, or it gets rolled back too.
- Skip on checksum, not file name. Compare against the *current* version, not "any previous load": a failed load is never current, and resending an older version is a real change.
- Off-by-one: `2024-03-31` is in Q1 and `2024-04-01` is not.

</details>

<details><summary>Check yourself</summary>

Running the six files in the order listed above, all as `s01`/`s02` with their quarters, gives:

| File | Status | row_count |
|---|---|---|
| `s01_2024Q1.csv` | loaded | 60 |
| `s01_2024Q1_resend.csv` | skipped | 0 |
| `s01_2024Q1_corrected.csv` | replaced | 59 |
| `s01_2024Q1_broken.csv` | failed (`line 41: ...`, a date of 2024-04-01) | 0 |
| `s01_2024Q2.csv` | loaded | 55 |
| `s02_2024Q1.csv` | loaded | 40 |

`lab_results` ends with 59 + 55 + 40 = **154** rows.

</details>

## Say it out loud

- **Restate:** the load is a function of (site, quarter, file bytes). Running it twice changes nothing, a correction swaps one partition, and a bad file changes nothing except the audit log.
- **Edge cases:** identical bytes under a new name, resending an older version, a broken file as the very first load, a header-only file (don't let an empty export wipe a quarter), quarter boundaries, a DB error halfway through the insert.
- **Plan:** checksum, look up the current version, then skip, validate, and replace in one transaction. Audit every attempt.
- **Complexity:** O(n) to hash and validate, O(n) to insert. The delete is O(rows in the partition) with an index on `(site_id, quarter)`.
- **At 100x:** stream the checksum (already chunked) and validate in a streaming pass to a staging table, then swap partitions. DELETE+INSERT on a huge table becomes a partition overwrite.
- **Pedestal mapping:** the S3 object's ETag or SHA in a manifest is the checksum. Step Functions runs `load_quarter` per (site, quarter). In Iceberg, a corrected resend is an `INSERT OVERWRITE` / `overwrite_partitions` on `(site_id, quarter)`: one atomic snapshot commit, and time travel to the prior snapshot is your rollback. The audit table is what dbt source freshness and your quality dashboards read. In dbt, this is an incremental model with `insert_overwrite` on the partition, not `append`.
