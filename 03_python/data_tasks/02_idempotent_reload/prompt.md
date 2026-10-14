# 02. The site resent Q1

**Timebox: 35 min** | Write: `03_python/data_tasks/02_idempotent_reload/solution.py`

## Input

Files in `data/`. `load_quarter(conn, site_id, quarter, path)` loads one of
them as `path`. `python gen_data.py` regenerates them byte-identically.

| File | What it is |
|---|---|
| `s01_2024Q1.csv` | Site s01, Q1: 60 rows |
| `s01_2024Q1_resend.csv` | Byte-identical to the Q1 file, different name |
| `s01_2024Q1_corrected.csv` | 59 rows: three rows corrected (same `patient_id` and `collected_date`, new `test_code`, `value` and `unit`), two rows withdrawn, one late row added |
| `s01_2024Q1_broken.csv` | The corrected file with one bad row partway through |
| `s01_2024Q2.csv` | Site s01, Q2: 55 rows |
| `s02_2024Q1.csv` | Site s02, Q1: 40 rows |

File: each CSV above (comma-separated, UTF-8, header row)

```text
+----------------+------+----------------------------------------+
| Column Name    | Type | Notes                                  |
+----------------+------+----------------------------------------+
| patient_id     | text | e.g. 'P0016' (s01) or 'Q0024' (s02)    |
| test_code      | text | 'GLU', 'HBA1C', 'K' or 'CREAT'         |
| collected_date | text | YYYY-MM-DD                             |
| value          | text | a number, e.g. '0.93'                  |
| unit           | text | e.g. 'mg/dL'                           |
+----------------+------+----------------------------------------+
```

Every file has the header `patient_id,test_code,collected_date,value,unit`.

Other arguments:

- `conn`: an open `sqlite3.Connection`. `init_db(conn)` creates the two
  tables below.
- `site_id` (`str`): e.g. `'s01'`.
- `quarter` (`str`): a label like `'2024Q1'`.

Database: sqlite3, with the tables from `SCHEMA_SQL` in `solution.py`. Don't
change table or column names.

Table: `lab_results`

```text
+----------------+------+--------------------------+
| Column Name    | Type | Notes                    |
+----------------+------+--------------------------+
| site_id        | TEXT | NOT NULL, e.g. 's01'     |
| quarter        | TEXT | NOT NULL, e.g. '2024Q1'  |
| patient_id     | TEXT | NOT NULL                 |
| test_code      | TEXT | NOT NULL                 |
| collected_date | TEXT | NOT NULL, YYYY-MM-DD     |
| value          | REAL | NOT NULL                 |
| unit           | TEXT | NOT NULL                 |
+----------------+------+--------------------------+
```

One row per loaded lab result. A site-quarter is all the rows with one
(`site_id`, `quarter`).

Table: `load_audit`

```text
+-------------+---------+---------------------------------------------------+
| Column Name | Type    | Notes                                             |
+-------------+---------+---------------------------------------------------+
| load_id     | INTEGER | primary key, autoincrement                        |
| site_id     | TEXT    | NOT NULL                                          |
| quarter     | TEXT    | NOT NULL                                          |
| file_name   | TEXT    | NOT NULL; the base name, Path(path).name          |
| checksum    | TEXT    | NOT NULL; SHA-256 hex digest of the file's bytes  |
| row_count   | INTEGER | NOT NULL                                          |
| status      | TEXT    | NOT NULL; loaded, replaced, skipped or failed     |
| message     | TEXT    | NOT NULL, default ''                              |
| loaded_at   | TEXT    | NOT NULL; any timestamp you like (not tested)     |
+-------------+---------+---------------------------------------------------+
```

One row per `load_quarter` call, except a call with a bad quarter label.

Sites resend quarters. Sometimes the bytes are identical (someone re-ran the
export), sometimes it's a real correction, and sometimes the new file is
broken. The loader has to do the right thing every time, and a rerun must
never double-count. Build it on `sqlite3` so the tests run anywhere. In
production this would be Postgres or an Iceberg table, but the logic is the
same.

## Task

**Goal:** each `load_quarter(conn, site_id, quarter, path)` call with a valid
quarter label adds exactly one `load_audit` row and returns its `status`.
After every call, the `lab_results` rows for (`site_id`, `quarter`) are
exactly the rows of the last file that loaded for that pair. A rerun of the
same bytes, a bad file or a database error leaves them as they were.

Steps 1-4 are the helper functions. Steps 5-9 are `load_quarter`.

1. **Create the tables.** `init_db(conn)` runs `SCHEMA_SQL` and commits. Both
   statements are `CREATE TABLE IF NOT EXISTS`, so a second call changes
   nothing.
2. **Parse the quarter label.** `parse_quarter(quarter)` accepts exactly 4
   digits, a capital `Q`, and one digit from 1 to 4 (`'2024Q1'`). Anything
   else (`'2024Q5'`, `'2024Q0'`, `'24Q1'`, `'2024-Q1'`, `'2024q1'`, `''`)
   raises `ValueError`. It returns (start, end) as `date`s: start is the first
   day of the quarter, end is the first day of the next quarter.
   - Q1 -> (YYYY-01-01, YYYY-04-01)
   - Q2 -> (YYYY-04-01, YYYY-07-01)
   - Q3 -> (YYYY-07-01, YYYY-10-01)
   - Q4 -> (YYYY-10-01, January 1 of the next year)

   Start is inclusive and end is exclusive.
3. **Checksum the file.** `file_checksum(path)` returns the SHA-256 hex digest
   (64 lowercase hex characters) of the file's raw bytes. Two files with the
   same bytes have the same checksum, whatever their names.
4. **Read and validate the file.** `read_and_validate(path, quarter)` reads
   the whole file as CSV (UTF-8) before anything touches the database. Line 1
   is the header and line 2 is the first data row. Check the lines in order,
   and stop at the first bad one: raise `ValueError` with a message that
   starts `line N:`, where N is that line's number.
   1. Line 1 must be exactly `patient_id,test_code,collected_date,value,unit`.
      A missing or different header fails as `line 1:`.
   2. Each data line must have exactly 5 fields.
   3. `patient_id.strip()` and `test_code.strip()` must not be empty.
   4. `collected_date.strip()` must have the form `YYYY-MM-DD` and be a real
      date (`'2024-02-30'` and `'02/01/2024'` fail). It must fall in the
      quarter: start <= date < end, with start and end from step 2.
   5. `float(value.strip())` must work and give a finite number (`'abc'`,
      `''` and `'nan'` fail).

   `unit` is not checked. If the file has no data lines, raise `ValueError`
   too (any message). Otherwise return one tuple per data line, in file
   order: (`patient_id.strip()`, `test_code.strip().upper()`,
   `collected_date.strip()`, `float(value.strip())`, `unit.strip()`).
5. **Check the label and find the current version.** `load_quarter` first
   calls `parse_quarter(quarter)`. A bad label raises `ValueError` before
   anything is written, so that call adds no `load_audit` row. Then it finds
   the current version of (`site_id`, `quarter`): the `load_audit` row with
   the highest `load_id` among rows with this `site_id`, this `quarter` and
   `status IN ('loaded', 'replaced')`. A `failed` or `skipped` row is never
   the current version. There may be no current version.
6. **Skip identical bytes.** If there is a current version and
   `file_checksum(path)` equals its `checksum`, add a `skipped` audit row with
   `row_count` 0 and return `'skipped'`. `lab_results` doesn't change. Only
   the current version counts: the same file for another `site_id` or
   `quarter` is not skipped, and neither is a file whose bytes match an older
   version.
7. **Validate.** Call `read_and_validate(path, quarter)`. If it raises
   `ValueError`, add a `failed` audit row with `row_count` 0 and `message` =
   `str(error)`, and return `'failed'`. `lab_results` doesn't change, so a
   header-only file can't wipe a quarter.
8. **Replace the site-quarter in one transaction.** The status is
   `'replaced'` if step 5 found a current version, else `'loaded'`. In one
   transaction:
   - delete every `lab_results` row with this `site_id` and this `quarter`
     (rows of other sites and quarters stay),
   - insert one row per step 4 tuple, with `site_id` and `quarter` from the
     arguments,
   - add the audit row with that status, `row_count` = the number of rows
     inserted and `message` `''`.

   Commit, and return the status.
9. **Roll back on a database error.** If any statement in step 8 raises
   `sqlite3.Error`, roll back the whole step 8 transaction: the delete is
   undone and the prior rows are back. Then, in a new transaction, add a
   `failed` audit row with `row_count` 0 and `message` = `str(error)`, commit
   it, and return `'failed'`. This row is not a current version, so the next
   try with the same file is not skipped.

Every audit row from steps 6-9 has `site_id` and `quarter` from the
arguments, `file_name` = `Path(path).name`, `checksum` = `file_checksum(path)`
and `loaded_at` = the time of the call as text. It is committed before
`load_quarter` returns, and no transaction is left open
(`conn.in_transaction` is `False`).

## Output

| function | returns |
|---|---|
| `init_db(conn)` | `None`; both tables exist (step 1) |
| `file_checksum(path)` | `str`: 64 hex characters (step 3) |
| `parse_quarter(quarter)` | `tuple[date, date]`: (start, end), end exclusive (step 2) |
| `read_and_validate(path, quarter)` | `list[tuple[str, str, str, float, str]]`: (`patient_id`, `test_code`, `collected_date`, `value`, `unit`) per data line (step 4) |
| `load_quarter(conn, site_id, quarter, path)` | `str`: the status of the audit row it added: `'loaded'`, `'replaced'`, `'skipped'` or `'failed'` |

Table `lab_results`, one row per tuple inserted in step 8:

| # | column | notes |
|---|---|---|
| 1 | site_id | the `site_id` argument |
| 2 | quarter | the `quarter` argument |
| 3 | patient_id | `patient_id.strip()` |
| 4 | test_code | `test_code.strip().upper()` |
| 5 | collected_date | `collected_date.strip()`, `YYYY-MM-DD` |
| 6 | value | `float(value.strip())` |
| 7 | unit | `unit.strip()` |

Table `load_audit`, one row per `load_quarter` call (none for a bad label):

| # | column | notes |
|---|---|---|
| 1 | load_id | autoincrement: 1, 2, 3, ... in call order |
| 2 | site_id | the `site_id` argument |
| 3 | quarter | the `quarter` argument |
| 4 | file_name | `Path(path).name` |
| 5 | checksum | `file_checksum(path)`, for every status |
| 6 | row_count | rows inserted for `loaded` and `replaced`; 0 for `skipped` and `failed` |
| 7 | status | `loaded` or `replaced` (step 8), `skipped` (step 6), `failed` (step 7 or 9) |
| 8 | message | `''` unless `failed`. For `failed`: `str(error)`, which starts `line N:` for a bad line |
| 9 | loaded_at | the time of the call, any text (not tested) |

## Example

Five small files, each written by `csv.writer` (lines end in `\r\n`). The
spaces are in the files.

```text
a.csv and a_copy.csv (the same bytes under two names):
patient_id,test_code,collected_date,value,unit
P0001,GLU,2024-01-01,99,mg/dL
 P0002 , k ,2024-03-31, 4.1 ,mmol/L

b.csv (a correction of a.csv):
patient_id,test_code,collected_date,value,unit
P0001,GLU,2024-01-01,104,mg/dL
P0003,HBA1C,2024-02-29,6.1,%

bad.csv:
patient_id,test_code,collected_date,value,unit
P0001,GLU,2024-01-01,99,mg/dL
P0002,K,2024-04-01,4.1,mmol/L

empty.csv (header only):
patient_id,test_code,collected_date,value,unit
```

Calls, in this order, on a new database:

```python
conn = sqlite3.connect(":memory:")
init_db(conn)
load_quarter(conn, "s01", "2024Q5", "a.csv")       # call 1: raises ValueError
load_quarter(conn, "s01", "2024Q1", "bad.csv")     # call 2: 'failed'
load_quarter(conn, "s01", "2024Q1", "a.csv")       # call 3: 'loaded'
load_quarter(conn, "s01", "2024Q1", "a_copy.csv")  # call 4: 'skipped'
load_quarter(conn, "s02", "2024Q1", "a.csv")       # call 5: 'loaded'
load_quarter(conn, "s01", "2024Q1", "b.csv")       # call 6: 'replaced'
load_quarter(conn, "s01", "2024Q1", "empty.csv")   # call 7: 'failed'
load_quarter(conn, "s01", "2024Q1", "a.csv")       # call 8: 'replaced'
conn.execute("CREATE TRIGGER boom BEFORE INSERT ON lab_results"
             " WHEN NEW.patient_id = 'P0003' BEGIN SELECT RAISE(ABORT, 'boom'); END")
conn.commit()                                      # inserting P0003 now fails
load_quarter(conn, "s01", "2024Q1", "b.csv")       # call 9: 'failed'
```

Output: the return values are in the comments above. The tables after call 9
(`loaded_at` left out, checksums cut to 8 of their 64 hex digits):

`lab_results`:

```text
+---------+---------+------------+-----------+----------------+-------+--------+
| site_id | quarter | patient_id | test_code | collected_date | value | unit   |
+---------+---------+------------+-----------+----------------+-------+--------+
| s01     | 2024Q1  | P0001      | GLU       | 2024-01-01     | 99.0  | mg/dL  |
| s01     | 2024Q1  | P0002      | K         | 2024-03-31     | 4.1   | mmol/L |
| s02     | 2024Q1  | P0001      | GLU       | 2024-01-01     | 99.0  | mg/dL  |
| s02     | 2024Q1  | P0002      | K         | 2024-03-31     | 4.1   | mmol/L |
+---------+---------+------------+-----------+----------------+-------+--------+
```

`load_audit`:

```text
+---------+---------+---------+------------+-------------+-----------+----------+-----------------------------------------------------+
| load_id | site_id | quarter | file_name  | checksum    | row_count | status   | message                                             |
+---------+---------+---------+------------+-------------+-----------+----------+-----------------------------------------------------+
| 1       | s01     | 2024Q1  | bad.csv    | 70241365... | 0         | failed   | line 3: collected_date 2024-04-01 is outside 2024Q1 |
| 2       | s01     | 2024Q1  | a.csv      | 39c57bfb... | 2         | loaded   |                                                     |
| 3       | s01     | 2024Q1  | a_copy.csv | 39c57bfb... | 0         | skipped  |                                                     |
| 4       | s02     | 2024Q1  | a.csv      | 39c57bfb... | 2         | loaded   |                                                     |
| 5       | s01     | 2024Q1  | b.csv      | dbe036a3... | 2         | replaced |                                                     |
| 6       | s01     | 2024Q1  | empty.csv  | 0b2eac56... | 0         | failed   | no data rows                                        |
| 7       | s01     | 2024Q1  | a.csv      | 39c57bfb... | 2         | replaced |                                                     |
| 8       | s01     | 2024Q1  | b.csv      | dbe036a3... | 0         | failed   | boom                                                |
+---------+---------+---------+------------+-------------+-----------+----------+-----------------------------------------------------+
```

The wording after `line 3:` is up to you, and so is the no-data-rows message.
The tests check only the `line N:` start.

Explanation:

- **Step 1.** `init_db` creates both tables, empty. A second call would change
  nothing.
- **Step 2.** `'2024Q1'` gives (2024-01-01, 2024-04-01). `'2024Q5'` is not a
  label, so call 1 raises `ValueError` and writes nothing: load_id 1 belongs
  to call 2.
- **Step 3.** `a.csv` and `a_copy.csv` have the same bytes, so the same
  checksum (`39c57bfb...`). `b.csv` has other bytes and another checksum.
- **Step 4.** In `a.csv`, 2024-01-01 (the first day of Q1) and 2024-03-31 (the
  last day) are both in the quarter. Line 3 becomes (`'P0002'`, `'K'`,
  `'2024-03-31'`, 4.1, `'mmol/L'`). In `bad.csv`, line 3 has 2024-04-01, the
  first day of Q2: `line 3: ...`. `empty.csv` has no data lines, so it fails
  too.
- **Step 5.** At call 2 there is no current version, and a failed row doesn't
  make one, so call 3 is `loaded`, not `replaced`. For (`s01`, `2024Q1`) the
  current version is load_id 2 at calls 4 and 6, load_id 5 at calls 7 and 8,
  and load_id 7 at call 9. (`s02`, `2024Q1`) has none at call 5.
- **Step 6.** Call 4: `a_copy.csv` has a new name but the current version's
  checksum, so it is `skipped`. Call 5: the same bytes as `a.csv`, but for
  `s02`, which has no current version: `loaded`. Call 8: `a.csv` matches
  load_id 2, but the current version is load_id 5 (`b.csv`), so it is not
  skipped.
- **Step 7.** Call 2 fails at line 3, and nothing is loaded. Call 7 fails, so
  the `b.csv` rows stay: a header-only file doesn't wipe the quarter.
- **Step 8.** Call 6 deletes only the 2 `s01`/`2024Q1` rows and inserts the 2
  rows of `b.csv`: P0001's GLU becomes 104.0, P0002 is withdrawn and P0003 is
  added. The `s02` rows don't change. Call 8 swaps back to the rows of
  `a.csv`: resending an older version is a real change.
- **Step 9.** Call 9 deletes the `s01`/`2024Q1` rows and inserts P0001, then
  inserting P0003 raises `sqlite3.Error` (`boom`). The rollback undoes the
  delete and the insert, so `s01` still holds the rows of `a.csv`. The
  `failed` audit row (load_id 8) is written after the rollback, so it stays.

## Implement (in `solution.py`)

```python
def init_db(conn) -> None
def file_checksum(path) -> str
def parse_quarter(quarter) -> tuple[date, date]               # (start, end_exclusive)
def read_and_validate(path, quarter) -> list[tuple[str, str, str, float, str]]
def load_quarter(conn, site_id, quarter, path) -> str          # loaded|replaced|skipped|failed
```

Keep the names and signatures: the tests import them. The docstrings in
`solution.py` are part of the spec.

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
- **Complexity:** O(n) to hash and validate, O(n) to insert. `SCHEMA_SQL` has no index, so the DELETE and the current-version lookup scan their whole tables. With an index on `(site_id, quarter)`, the delete is O(rows in the partition).
- **At 100x:** hash the file in chunks and validate in a streaming pass to a staging table, then swap partitions. DELETE+INSERT on a huge table becomes a partition overwrite.
- **Pedestal mapping:** the S3 object's ETag or a SHA in a manifest is the checksum (a multipart upload's ETag is not a hash of the whole file, so a SHA you record is safer). Step Functions runs `load_quarter` per (site, quarter). In Iceberg, a corrected resend is an `INSERT OVERWRITE` / `overwrite_partitions` on `(site_id, quarter)`: one atomic snapshot commit, and time travel to the prior snapshot is your rollback. The audit table is what dbt source freshness and your quality dashboards read. In dbt, this is an incremental model with `insert_overwrite` on the partition, not `append`.
