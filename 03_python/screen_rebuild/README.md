# Screen rebuild

Same shape as the CoderPad task, with the mess left in. Write it in pandas first, then redo it with only the standard library
(queue blocks `screen-pandas`, `screen-tests`, `screen-stdlib`).

## Input

Files in `data/`. `python make_data.py` regenerates everything identically (fixed seed).

File: `data/transactions.csv` (comma-separated, header row, standard CSV quoting): 200 transactions with planted problems.

```text
+------------------+------+------------------------------------+
| Column Name      | Type | Notes                              |
+------------------+------+------------------------------------+
| transaction_id   | text | e.g. 'T000012'                     |
| transaction_date | text | YYYY-MM-DD                         |
| product_code     | text | e.g. 'P039'; looked up in products |
| quantity         | text | a positive integer, e.g. '2'       |
| unit_price       | text | e.g. '11.51'                       |
| store_id         | text | e.g. 'S07'                         |
| notes            | text | free text, can be blank            |
+------------------+------+------------------------------------+
```

`python make_data.py --big N` also writes `data/transactions_big.csv` (gitignored) with N rows and the same columns.

Table: `products` in `data/products.db` (SQLite). `data/products.sql` has the same table as SQL, if you'd rather load it into Postgres.

```text
+--------------+---------+------------------------------------+
| Column Name  | Type    | Notes                              |
+--------------+---------+------------------------------------+
| product_id   | INTEGER | primary key                        |
| product_code | TEXT    | NOT NULL, e.g. 'P001'              |
| product_name | TEXT    | NOT NULL, e.g. 'Ibuprofen 200mg'   |
| is_active    | INTEGER | NOT NULL; 1 = active, 0 = inactive |
+--------------+---------+------------------------------------+
```

Product reference data. `product_code` in the transactions refers to this table's `product_code`.

## Task

Write `standardize.py` that:

1. Reads `data/transactions.csv`.
2. Replaces `product_code` with `product_name` from the products table.
3. Writes `output/standardized_transactions.csv` with columns
   `transaction_id, transaction_date, product_name, quantity, unit_price, store_id, notes`, sorted by `transaction_id`.
4. Writes `output/rejects.csv`: the original fields plus a `reject_reason` column.
5. Prints a short run summary: rows read, rows written, rows rejected by reason, duplicates dropped.

## Rules (apply in this order)

| # | Rule | Reject reason |
|---|---|---|
| 1 | A line with the wrong number of fields is rejected | `wrong_column_count` |
| 2 | Exact duplicate rows: keep one, drop the rest (not rejects) | |
| 3 | Same `transaction_id` with different values: reject every version | `conflicting_duplicate` |
| 4 | Date must be a real `YYYY-MM-DD` date | `invalid_date` |
| 5 | Codes are matched after trimming whitespace and uppercasing | |
| 6 | Empty code | `missing_product_code` |
| 7 | Code not among **active** products | `unknown_product_code` |
| 8 | Quantity must be a positive integer | `invalid_quantity` |

Read the products table before you write the join. Something in it will bite you.

## Check yourself (don't look until you've run it)

<details><summary>Expected counts</summary>

- Written: **192** rows
- Rejected: **11** rows: `wrong_column_count` 2, `conflicting_duplicate` 2, `unknown_product_code` 3, `invalid_quantity` 2, `missing_product_code` 1, `invalid_date` 1
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

## Say it out loud while you work

Before coding: restate the task, name the edge cases you see, state your plan. After: complexity, and what changes if the file is 50 GB (the `screen-stdlib` question).
