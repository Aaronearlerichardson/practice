# Screen rebuild

**Timebox: 25 min** | Write: `03_python/screen_rebuild/standardize.py`

Same shape as the CoderPad task, with the mess left in. Write it in pandas first, then redo it with only the standard library
(queue blocks `screen-pandas` 25 min, `screen-tests` 20 min, `screen-stdlib` 25 min).

## Input

Files in `data/`. `python make_data.py` regenerates everything identically (fixed seed). Paths in this README are
relative to `03_python/screen_rebuild/`.

File: `data/transactions.csv` (comma-separated, header row, standard CSV quoting): 206 lines after the header, with
planted problems.

```text
+------------------+------+--------------------------------------------------------------+
| Column Name      | Type | Notes                                                        |
+------------------+------+--------------------------------------------------------------+
| transaction_id   | text | e.g. 'T000012'; not unique in the file                       |
| transaction_date | text | should be 'YYYY-MM-DD'; can be an impossible date            |
| product_code     | text | e.g. 'P039'; can be blank, padded or lowercase (' p012 ')    |
| quantity         | text | should be a positive integer, e.g. '2'; can be blank or text |
| unit_price       | text | e.g. '11.51'                                                 |
| store_id         | text | e.g. 'S07'                                                   |
| notes            | text | free text, can be blank; can hold commas and quotes          |
+------------------+------+--------------------------------------------------------------+
```

Most lines have these 7 fields. A few have more or fewer. A quoted field can hold commas and doubled quotes
(`"customer said ""rush"""`).

`python make_data.py --big N` also writes `data/transactions_big.csv` (gitignored) with N clean rows and the same columns.

Table: `products` in `data/products.db` (SQLite). `data/products.sql` has the same table as SQL, if you'd rather load it into Postgres.

```text
+--------------+---------+------------------------------------------+
| Column Name  | Type    | Notes                                    |
+--------------+---------+------------------------------------------+
| product_id   | INTEGER | primary key                              |
| product_code | TEXT    | NOT NULL, e.g. 'P001'; no UNIQUE         |
| product_name | TEXT    | NOT NULL, e.g. 'Ibuprofen 200mg'         |
| is_active    | INTEGER | NOT NULL; 1 = active, 0 = inactive       |
+--------------+---------+------------------------------------------+
```

Product reference data. `product_code` in the transactions refers to this table's `product_code`. Read the products
table before you write the join. Something in it will bite you.

## Task

**Goal:** write one output row per transaction line that passes every rule, with `product_code` replaced by its
`product_name`. Write every rejected line to a rejects file with one reason, and print a run summary.

Steps 1, 8 and 9 are `main()`. Step 2 is `load_products(db_path)`. Steps 3-7 are
`standardize(rows, code_to_name)` (see Implement below for this suggested shape).

1. **Read the lines.** Read `data/transactions.csv` with standard CSV quoting, every field as text. Skip the header.
   Each line after the header is one row of fields, and `rows read` counts all of them.
2. **Load the active products.** Build `code_to_name` from the `products` rows with `is_active = 1`:
   `product_code.strip().upper()` -> `product_name`. Rows with `is_active = 0` are left out.
3. **Reject lines with the wrong field count.** A line with more or fewer than 7 fields gets `wrong_column_count`.
   It is not checked further.
4. **Drop exact duplicates.** Among the remaining lines, lines whose 7 fields are all identical, as read, are exact
   duplicates. Keep the first one and drop the others. Dropped lines are not rejects: `duplicates dropped` counts
   them.
5. **Reject conflicting duplicates.** After step 4, when two or more lines share a `transaction_id` (as read), they
   differ in some field. Every one of them gets `conflicting_duplicate`, and none is written to the output.
6. **Check each remaining line.** Check these in order. The first rule a line fails gives its reason, and the line
   is not checked further. Here the normalized code is `product_code.strip().upper()`.
   - **6a.** `transaction_date` must be a real calendar date written `YYYY-MM-DD` (4 digits, `-`, 2 digits, `-`, 2
     digits). `2026-13-40` and `2026-02-30` fail: `invalid_date`.
   - **6b.** The normalized code must not be `""`: `missing_product_code`.
   - **6c.** The normalized code must be a key of `code_to_name` (step 2), so a code with only inactive rows fails
     too: `unknown_product_code`.
   - **6d.** `quantity` must be a positive integer: only the digits `0`-`9`, with a value of at least 1. `''`,
     `'two'`, `'0'`, `'-1'` and `'2.5'` fail: `invalid_quantity`.
7. **Build the output rows.** For each line that passes step 6, `product_name` = `code_to_name[normalized code]`.
   Every other column is copied as read (`11.50` stays `11.50`, and `notes` keeps its commas and quotes). Sort the
   output rows by `transaction_id`. Sort the reject rows by `transaction_id`. Rejects that share a
   `transaction_id` keep their file order.
8. **Write the two files.** Write `output/standardized_transactions.csv` and `output/rejects.csv` (columns below),
   each with a header row and standard CSV quoting.
9. **Print the run summary.** Print exactly these lines, with every reason listed in rule order, even when its count
   is 0:

   ```text
   rows read: <step 1 count>
   rows written: <output rows>
   rows rejected: <reject rows>
     wrong_column_count: <n>
     conflicting_duplicate: <n>
     invalid_date: <n>
     missing_product_code: <n>
     unknown_product_code: <n>
     invalid_quantity: <n>
   duplicates dropped: <step 4 count>
   ```

   The counts reconcile: rows read = rows written + rows rejected + duplicates dropped.

**Rules table:** steps 3-6 at a glance, in the order they run.

| # | Rule | Reject reason |
|---|---|---|
| 1 | A line with more or fewer than 7 fields is rejected (step 3) | `wrong_column_count` |
| 2 | Exact duplicate lines: keep the first, drop the rest. They are not rejects (step 4) | |
| 3 | Same `transaction_id` with different values: reject every version (step 5) | `conflicting_duplicate` |
| 4 | `transaction_date` must be a real `YYYY-MM-DD` date (step 6a) | `invalid_date` |
| 5 | Codes are matched after `strip()` and `upper()`, on both sides of the join (steps 2 and 6) | |
| 6 | Empty normalized code (step 6b) | `missing_product_code` |
| 7 | Normalized code not among the **active** products (step 6c) | `unknown_product_code` |
| 8 | `quantity` must be a positive integer (step 6d) | `invalid_quantity` |

## Output

`output/standardized_transactions.csv`: one row per line that passes step 6, sorted by `transaction_id`. Columns in
this order:

| # | column | notes |
|---|---|---|
| 1 | transaction_id | as read |
| 2 | transaction_date | as read |
| 3 | product_name | `code_to_name[product_code.strip().upper()]` (step 7) |
| 4 | quantity | as read |
| 5 | unit_price | as read, e.g. `11.50` stays `11.50` |
| 6 | store_id | as read |
| 7 | notes | as read, commas and quotes included |

`output/rejects.csv`: one row per rejected line (steps 3, 5 and 6), sorted by `transaction_id`, ties in file order.
Columns in this order:

| # | column | notes |
|---|---|---|
| 1-7 | transaction_id, transaction_date, product_code, quantity, unit_price, store_id, notes | the line's fields as read, in order. A `wrong_column_count` line with fewer than 7 fields leaves the missing columns blank. One with more than 7 keeps its first 7, and the extra fields are dropped |
| 8 | reject_reason | the reason from step 3, 5 or 6 |

Printed run summary: the step 9 lines.

## Example

Try it on your code (inputs editable): `python tasks.py try screen`.

Input `data/transactions.csv` (12 lines after the header):

```text
transaction_id,transaction_date,product_code,quantity,unit_price,store_id,notes
T000003,2026-03-01, p012 ,2,11.50,S01,"gift, wrapped"
T000001,2026-03-02,P017,1,4.25,S02,
T000002,2026-03-02,P005,3,9.99,S03,"customer said ""rush"""
T000002,2026-03-02,P005,3,9.99,S03,"customer said ""rush"""
T000004,2026-03-03,P006,5,43.19,S02,
T000004,2026-03-03,P006,99,43.19,S02,
T000005,2026-02-30,Q001,10,13.63,S01,
T000006,2026-03-04,,4,18.03,S01,
T000007,2026-03-04,P999,two,49.90,S03,
T000008,2026-03-05,P006,0,36.94,S07,
T009001,2026-05-05,P003,4,12.50,S02,,EXTRA_FIELD
T009002,2026-05-06,P004
```

Input `products`: the real table. The rows these lines use:

```text
+------------+--------------+---------------------------+-----------+
| product_id | product_code | product_name              | is_active |
+------------+--------------+---------------------------+-----------+
| 5          | P005         | Insulin Pen Needle        | 1         |
| 6          | P006         | Alcohol Prep Pad          | 1         |
| 12         | P012         | Surgical Mask             | 1         |
| 17         | P017         | Lancet 28G                | 1         |
| 41         | P017         | Lancet 30G (discontinued) | 0         |
+------------+--------------+---------------------------+-----------+
```

`output/standardized_transactions.csv`:

```text
transaction_id,transaction_date,product_name,quantity,unit_price,store_id,notes
T000001,2026-03-02,Lancet 28G,1,4.25,S02,
T000002,2026-03-02,Insulin Pen Needle,3,9.99,S03,"customer said ""rush"""
T000003,2026-03-01,Surgical Mask,2,11.50,S01,"gift, wrapped"
```

`output/rejects.csv`:

```text
transaction_id,transaction_date,product_code,quantity,unit_price,store_id,notes,reject_reason
T000004,2026-03-03,P006,5,43.19,S02,,conflicting_duplicate
T000004,2026-03-03,P006,99,43.19,S02,,conflicting_duplicate
T000005,2026-02-30,Q001,10,13.63,S01,,invalid_date
T000006,2026-03-04,,4,18.03,S01,,missing_product_code
T000007,2026-03-04,P999,two,49.90,S03,,unknown_product_code
T000008,2026-03-05,P006,0,36.94,S07,,invalid_quantity
T009001,2026-05-05,P003,4,12.50,S02,,wrong_column_count
T009002,2026-05-06,P004,,,,,wrong_column_count
```

Printed:

```text
rows read: 12
rows written: 3
rows rejected: 8
  wrong_column_count: 2
  conflicting_duplicate: 2
  invalid_date: 1
  missing_product_code: 1
  unknown_product_code: 1
  invalid_quantity: 1
duplicates dropped: 1
```

Explanation:

- **Step 1.** 12 lines after the header, so `rows read` is 12. The quoted notes keep their comma and their quotes.
- **Step 2.** `P017` has two products rows. Only `Lancet 28G` has `is_active = 1`, so `code_to_name['P017']` is
  `Lancet 28G`, and T000001 comes out once.
- **Step 3.** T009001 has 8 fields and T009002 has 3: both are `wrong_column_count`. In rejects, T009001 loses
  `EXTRA_FIELD` and T009002 gets blank columns.
- **Step 4.** The two T000002 lines are identical, so one is dropped (`duplicates dropped: 1`) and the other goes
  on.
- **Step 5.** The two T000004 lines differ in `quantity` (5 and 99), so both are rejected.
- **Step 6.** T000005's `2026-02-30` is not a real date. Its code `Q001` is unknown too, but the date rule runs
  first. T000006 has an empty code. T000007's `P999` is unknown (its `quantity` `two` is never checked). T000008's
  quantity `0` is not positive.
- **Step 7.** `' p012 '` normalizes to `P012`, which maps to `Surgical Mask`. The output is sorted by
  `transaction_id`, so T000003 (first in the file) comes last. Its price `11.50` keeps both decimals.
- **Step 8.** Both files are written with standard quoting, so the notes come back as `"gift, wrapped"` and
  `"customer said ""rush"""`.
- **Step 9.** 12 = 3 written + 8 rejected + 1 dropped.

## Implement (suggested shape, in `standardize.py`)

```python
def load_products(db_path) -> dict[str, str]                # step 2: code_to_name
def standardize(rows, code_to_name) -> tuple[list, list]    # steps 3-7: (good, rejects), both sorted
def main() -> None                                          # steps 1, 8, 9: read, write, print
```

`rows` is the list of field lists after the header, one `list[str]` per line. `good` holds the output rows and
`rejects` the reject rows, each as a `list[str]` in the Output column order. `main` can get `duplicates dropped` as
rows read - rows written - rows rejected.

In the pandas version, `standardize` can take a DataFrame of the 7-field lines instead, with the
`wrong_column_count` lines found while reading. Build file paths from `Path(__file__).parent`, so the script works
from any folder.

## Run

```powershell
.\.venv\Scripts\python.exe 03_python\screen_rebuild\standardize.py
.\.venv\Scripts\python.exe -m pytest 03_python\screen_rebuild -q -p no:cacheprovider
```

<details><summary>Hints</summary>

- `pd.read_csv` raises on the 8-field line by default, and it quietly pads the 3-field line with NaN. Count fields
  yourself with `csv.reader`, or use `engine="python", on_bad_lines=<a function>` and still catch the padded line.
- Read every column as text (`dtype=str, keep_default_na=False`), so `11.50` stays `11.50` and a blank stays `""`.
- Compare the row count before and after the join.

</details>

## Check yourself (don't look until you've run it)

<details><summary>Expected counts</summary>

- Read: **206** lines
- Written: **192** rows
- Rejected: **11** rows: `wrong_column_count` 2, `conflicting_duplicate` 2, `invalid_date` 1, `missing_product_code` 1, `unknown_product_code` 3, `invalid_quantity` 2
- Exact duplicates dropped: **3**
- Rows mapped to `Lancet 28G`: **6**. If you got 198 rows written, your join fanned out on `P017`.
- The two rows whose `notes` contain a comma and a quote must survive unchanged.

</details>

## Tests (write these yourself in `tests/`)

Three pytest tests, each on a tiny in-memory input rather than the full file:

1. A code with surrounding whitespace and lowercase letters still maps to the right name.
2. A duplicate product code with one inactive row does not duplicate the transaction.
3. A conflicting `transaction_id` sends both versions to rejects and neither to output.

Structure `standardize.py` so these are easy: a pure function that takes rows and a code-to-name mapping and returns (good, rejects). If testing it is awkward, that's the design feedback.

`python -m pytest` doesn't put this folder on `sys.path`, so start each test file with
`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` before `import standardize`. `python tasks.py test screen`
runs them.

## Say it out loud while you work

Before coding: restate the task, name the edge cases you see, state your plan. After: complexity, and what changes if the file is 50 GB (the `screen-stdlib` question).

- In production you would also keep each rejected line's raw text and line number, so a `wrong_column_count` line
  loses nothing.
