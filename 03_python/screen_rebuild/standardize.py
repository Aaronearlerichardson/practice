import sqlite3
import csv
from collections import Counter  # fix
from collections.abc import Iterable
import os.path
from datetime import date
import re

pwd = os.path.dirname(__file__)
data_dir = os.path.join(pwd, "data")
out_dir = os.path.join(pwd, "output")

def load_products(db_path: str) -> dict[str, str]:
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("select product_code, product_name" \
    " from products where is_active = 1")
    # print(cursor.fetchall())
    out = {k.strip().upper(): v for k, v in cursor.fetchall()}  # fix: normalize the product side too
    return out

def standardize(rows: Iterable[list],
                code_to_name: dict[str, str]) -> tuple[list[tuple], list[tuple], int]:
        # steps 3-7: (good, rejects), both sorted
    goods: list[tuple] = []
    bads: list[tuple] = []
    template = tuple("" for _ in range(7))
    rows = list(rows)  # fix: two passes need a list
    rows_read = len(rows)  # fix
    seen = set()  # fix: step 4, drop exact copies (as read) first
    kept = []  # fix
    for r in rows:  # fix
        if len(r) != 7 or tuple(r) not in seen:  # fix
            kept.append(r)  # fix
        seen.add(tuple(r))  # fix
    id_counts = Counter(r[0] for r in kept if len(r) == 7)  # fix: step 5 needs every id's count up front
    for r in kept:  # fix
        code = r[2].strip().upper() if len(r) > 2 else ""  # fix: leave r as read
        reason = apply_standard(
            tuple(r), code, code_to_name.keys(), id_counts)  # fix
        if reason is None:
            name = code_to_name[code]  # fix
            goods.append((*r[:2], name, *r[3:]))
        elif reason == "dropped_duplicates":
            pass
        else:
            blank = list(template)
            for i, ri in enumerate(r):
                if i < 7:
                    blank[i] = ri
            bads.append((*blank, reason))

    goods.sort(key=lambda x: x[0])
    bads.sort(key=lambda x: x[0])
    return goods, bads, rows_read

def apply_standard(row: tuple, code: str, valid_codes: Iterable[str],  # fix
                    id_counts: Counter) -> str | None:  # fix: no mutable defaults
    
    if len(row) != 7:
        out = "wrong_column_count" 
    elif id_counts[row[0]] > 1:  # fix
        out = "conflicting_duplicate"
    elif not is_valid_time(row[1]):
        out = "invalid_date"
    elif code == "":  # fix
        out = "missing_product_code"
    elif code not in valid_codes:  # fix
        out = "unknown_product_code"
    elif not is_posint(row[3]):
        out = "invalid_quantity"
    else:
        out = None

    return out

def is_posint(quantity) -> bool:
    if not (quantity.isascii() and quantity.isdigit()):  # fix: digits 0-9 only, so "+3" and " 3" fail
        return False  # fix
    try:
        my_int = int(quantity)
    except ValueError:
        return False
    if my_int > 0:
        return True
    else:
        return False

def is_valid_time(text: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        date.fromisoformat(text)
        return True
    except ValueError:
        return False

def print_summary(rread, rwritten, rrejected, wrong, conflict,
                  inv_date, missing, unknown, inv_quant, dups):
    print(f"""
rows read: {rread}
rows written: {rwritten}
rows rejected: {rrejected}
  wrong_column_count: {wrong}
  conflicting_duplicate: {conflict}
  invalid_date: {inv_date}
  missing_product_code: {missing}
  unknown_product_code: {unknown}
  invalid_quantity: {inv_quant}
duplicates dropped: {dups}
        """.strip())  # fix: no blank first line or trailing spaces

def main() -> None:
    products_filename = os.path.join(data_dir, "products.db")
    products = load_products(products_filename)

    rows_written = 0
    rows_rejected = 0
    wrong_column_count = 0
    conflicting_duplicate = 0
    invalid_date = 0
    missing_product_code = 0
    unknown_product_code = 0
    invalid_quantity = 0
    duplicates_dropped = 0

    csv_filename = os.path.join(data_dir, "transactions.csv")
    with open(csv_filename, 'r', newline="") as f:  # fix
        reader = csv.reader(f)
        header = next(reader) # skip header
        g, b, rows_read = standardize(reader, products)
    
    good_filename = os.path.join(out_dir, "standardized_transactions.csv")
    with open(good_filename, 'w', newline="") as f:  # fix: no blank lines on Windows
        writer = csv.writer(f)
        writer.writerow(header[:2] + ["product_name"] + header[3:])  # fix
        for r in g:
            writer.writerow(r)
            rows_written += 1
    bad_filename = os.path.join(out_dir, "rejects.csv")  # fix
    with open(bad_filename, 'w', newline="") as f:  # fix
        writer = csv.writer(f)
        writer.writerow(header + ["reject_reason"])
        for r in b:
            writer.writerow(r)
            rows_rejected += 1
            if r[-1] == "wrong_column_count":
                wrong_column_count += 1
            elif r[-1] == "conflicting_duplicate":
                conflicting_duplicate += 1
            elif r[-1] == "invalid_date":
                invalid_date += 1
            elif r[-1] == "missing_product_code":
                missing_product_code += 1
            elif r[-1] == "unknown_product_code":
                unknown_product_code += 1
            elif r[-1] == "invalid_quantity":
                invalid_quantity += 1
            else:
                raise NotImplementedError("impossible")

    duplicates_dropped = rows_read - rows_written - rows_rejected  # fix: step 4 count
    print_summary(rows_read, rows_written, rows_rejected,
                  wrong_column_count, conflicting_duplicate,
                  invalid_date, missing_product_code,
                  unknown_product_code, invalid_quantity,
                  duplicates_dropped)


if __name__ == "__main__":
    main()                                   # steps 1, 8, 9: read, write, print
