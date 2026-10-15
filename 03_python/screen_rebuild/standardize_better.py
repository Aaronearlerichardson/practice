# REFERENCE SOLUTION (keys branch only)
"""Screen rebuild, stdlib version: standardize transactions.csv against the active products."""
import csv
import re
import sqlite3
from collections import Counter
from collections.abc import Callable, Iterable
from contextlib import closing
from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent


@dataclass(frozen=True)
class Transaction:
    """One 7-field line of transactions.csv, every field as read."""
    transaction_id: str
    transaction_date: str
    product_code: str
    quantity: str
    unit_price: str
    store_id: str
    notes: str

    @property
    def code(self) -> str:
        return self.product_code.strip().upper()

    def output_row(self, code_to_name: dict[str, str]) -> list[str]:
        """Step 7: the line as read, with product_code replaced by its product_name."""
        return [self.transaction_id, self.transaction_date, code_to_name[self.code],
                self.quantity, self.unit_price, self.store_id, self.notes]


IN_COLUMNS = [f.name for f in fields(Transaction)]
OUT_COLUMNS = ["product_name" if c == "product_code" else c for c in IN_COLUMNS]
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def is_real_date(text: str) -> bool:
    if not DATE_RE.fullmatch(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def is_positive_int(text: str) -> bool:
    return text.isascii() and text.isdigit() and int(text) >= 1


# Step 6: reject reason -> the test a line must pass. Dicts keep insertion order, so this is also the check order.
CHECKS: dict[str, Callable[[Transaction, dict[str, str]], bool]] = {
    "invalid_date": lambda t, names: is_real_date(t.transaction_date),
    "missing_product_code": lambda t, names: t.code != "",
    "unknown_product_code": lambda t, names: t.code in names,
    "invalid_quantity": lambda t, names: is_positive_int(t.quantity),
}
REASONS = ["wrong_column_count", "conflicting_duplicate", *CHECKS]  # every reason, in rule order


@dataclass
class Result:
    # default_factory, not `= []`: a dataclass refuses a shared mutable default outright.
    good: list[list[str]] = field(default_factory=list)
    rejects: list[list[str]] = field(default_factory=list)
    reasons: Counter[str] = field(default_factory=Counter)
    rows_read: int = 0
    dropped: int = 0

    def reject(self, row: list[str], reason: str) -> None:
        self.rejects.append([*row, reason])
        self.reasons[reason] += 1


def load_products(db_path: Path) -> dict[str, str]:
    """Step 2: active products only, keyed by the normalized code."""
    with closing(sqlite3.connect(db_path)) as db:
        rows = db.execute("SELECT product_code, product_name FROM products WHERE is_active = 1").fetchall()
    return {code.strip().upper(): name for code, name in rows}


def standardize(rows: Iterable[list[str]], code_to_name: dict[str, str]) -> Result:
    """Steps 3-7. `rows` is the field lists after the header. Returns good and reject rows, both sorted."""
    result = Result()
    seen: set[tuple[str, ...]] = set()
    kept: list[list[str]] = []
    for row in rows:
        result.rows_read += 1
        if len(row) == len(IN_COLUMNS):
            if tuple(row) in seen:  # step 4: an exact copy, dropped and not a reject
                result.dropped += 1
                continue
            seen.add(tuple(row))
        kept.append(row)

    # Step 5 needs every id's count before any line with that id is judged.
    id_counts = Counter(row[0] for row in kept if len(row) == len(IN_COLUMNS))

    for row in kept:  # file order, so rejects that share an id stay in file order after the stable sort
        if len(row) != len(IN_COLUMNS):  # step 3: pad short lines, cut long ones
            result.reject((row + [""] * len(IN_COLUMNS))[:len(IN_COLUMNS)], "wrong_column_count")
            continue
        t = Transaction(*row)
        if id_counts[t.transaction_id] > 1:
            result.reject(row, "conflicting_duplicate")
            continue
        reason = next((r for r, passes in CHECKS.items() if not passes(t, code_to_name)), None)
        if reason:
            result.reject(row, reason)
        else:
            result.good.append(t.output_row(code_to_name))

    result.good.sort(key=lambda r: r[0])
    result.rejects.sort(key=lambda r: r[0])
    return result


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def summary(result: Result) -> str:
    lines = [f"rows read: {result.rows_read}",
             f"rows written: {len(result.good)}",
             f"rows rejected: {len(result.rejects)}"]
    lines += [f"  {reason}: {result.reasons[reason]}" for reason in REASONS]
    lines.append(f"duplicates dropped: {result.dropped}")
    return "\n".join(lines)


def main() -> None:
    code_to_name = load_products(HERE / "data" / "products.db")
    with open(HERE / "data" / "transactions.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        result = standardize(reader, code_to_name)
    assert result.rows_read == len(result.good) + len(result.rejects) + result.dropped, "counts don't reconcile"

    out = HERE / "output"
    write_csv(out / "standardized_transactions.csv", OUT_COLUMNS, result.good)
    write_csv(out / "rejects.csv", [*IN_COLUMNS, "reject_reason"], result.rejects)
    print(summary(result))


if __name__ == "__main__":
    main()
