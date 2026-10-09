"""Task runner for the practice repo. Works the same in PowerShell, cmd, and bash.

    python tasks.py setup-db                 create the `practice` database, schema, and ~1.5M lab rows
    python tasks.py gen-data [--big N] [--big-mb MB]
                                             regenerate the file-based exercise data
    python tasks.py check-sql 03             check 02_sql/solutions/03_*.sql against its hash
    python tasks.py check-sql m1             (mock day) check mock/sql/solutions/m1_*.sql
    python tasks.py perf 13                  time a performance problem before and after your fix
    python tasks.py time-sql FILE            print EXPLAIN (ANALYZE, BUFFERS) and the median runtime of one query
    python tasks.py drop-indexes             remove every non-primary-key index you created
    python tasks.py test debugging [03]      run tests (areas: screen, debugging, data, mock, all)
    python tasks.py bench 05                 run a debugging exercise's benchmark
    python tasks.py hash-sql FILE            print the hash of a query result (used to build expected/)

Database connection: set PRACTICE_DSN, e.g. in PowerShell
    $env:PRACTICE_DSN = "postgresql://postgres:leet@localhost:5432/practice"
The default below matches the local `leetpg` Docker container.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import statistics
import subprocess
import sys
import time
from datetime import date, datetime, time as dtime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DSN = "postgresql://postgres:leet@localhost:5432/practice"
SQL_DIRS = {"": ROOT / "02_sql", "m": ROOT / "mock" / "sql"}
TABLES = ("sites", "patients", "enrollments", "encounters", "quarterly_loads", "labs")
STATEMENT_TIMEOUT_S = 300


def dsn() -> str:
    return os.environ.get("PRACTICE_DSN", DEFAULT_DSN)


def connect(autocommit: bool = True, dbname: str | None = None):
    import psycopg
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    info = dsn()
    if dbname:
        info = make_conninfo(info, dbname=dbname)
    try:
        return psycopg.connect(info, autocommit=autocommit)
    except psycopg.OperationalError as e:
        target = conninfo_to_dict(info)
        sys.exit(f"Could not connect to Postgres at {target.get('host')}:{target.get('port')} "
                 f"db={target.get('dbname')}.\nIs the container running? (docker start leetpg)\n{e}")


# ----------------------------------------------------------------------------- hashing

def norm(v) -> str:
    """Canonical text for one value, so int/numeric/float and column aliases don't matter."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float, Decimal)):
        d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
        if not d.is_finite():
            return str(d)
        d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return "0.00" if d == 0 else str(d)
    if isinstance(v, datetime):
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v.isoformat(sep=" ")
    if isinstance(v, (date, dtime)):
        return v.isoformat()
    if isinstance(v, timedelta):
        return norm(Decimal(str(v.total_seconds())))
    return str(v)


def digest(rows: list[tuple]) -> dict:
    """SHA-256 over normalized rows sorted as text. Row order in the query does not matter."""
    ncols = len(rows[0]) if rows else 0
    lines = sorted("\x1f".join(norm(v) for v in r) for r in rows)
    cols = []
    for i in range(ncols):
        vals = sorted(norm(r[i]) for r in rows)
        cols.append(hashlib.sha256("\n".join(vals).encode()).hexdigest()[:12])
    return {"sha256": hashlib.sha256("\n".join(lines).encode()).hexdigest(),
            "rows": str(len(rows)), "columns": str(ncols), "column_hashes": ",".join(cols)}


def read_expected(path: Path) -> dict:
    out = {}
    for ln in path.read_text().splitlines():
        if ":" in ln and not ln.startswith("#"):
            k, v = ln.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def run_query(sql: str, conn, read_only: bool = True) -> list[tuple]:
    sql = sql.strip()
    if not sql or all(ln.strip().startswith("--") or not ln.strip() for ln in sql.splitlines()):
        sys.exit("The solution file is empty. Write your query first.")
    with conn.cursor() as cur:
        if read_only:
            cur.execute("BEGIN READ ONLY")
        cur.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_S}s'" if read_only
                    else f"SET statement_timeout = '{STATEMENT_TIMEOUT_S}s'")
        cur.execute(sql)
        rows = None
        while True:  # take the last statement that returned rows
            if cur.description is not None:
                rows = cur.fetchall()
            if not cur.nextset():
                break
        if read_only:
            cur.execute("ROLLBACK")
    if rows is None:
        sys.exit("The file ran but returned no result set (is the last statement a SELECT?).")
    return rows


def find_problem(pid: str) -> tuple[Path, str]:
    """'3' / '03' / 'm1' -> (sql dir, stem like '03_rank_vs_dense_rank')."""
    prefix = "m" if pid.lower().startswith("m") else ""
    base = SQL_DIRS[prefix]
    num = pid.lower().lstrip("m")
    key = (prefix + num.zfill(2 if not prefix else 1)) if num.isdigit() else pid
    matches = sorted(base.glob(f"expected/{key}_*.sha256"))
    if not matches:
        sys.exit(f"No problem '{pid}' under {base.relative_to(ROOT)}/expected")
    return base, matches[0].stem


# ----------------------------------------------------------------------------- commands

def cmd_setup_db(a) -> None:
    from psycopg import sql as psql
    from psycopg.conninfo import conninfo_to_dict

    name = conninfo_to_dict(dsn()).get("dbname", "practice")
    with connect(dbname="postgres") as admin:
        exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            admin.execute(psql.SQL("CREATE DATABASE {}").format(psql.Identifier(name)))
            print(f"created database {name}", flush=True)
    with connect() as conn:
        conn.execute((ROOT / "02_sql" / "schema.sql").read_text())
    print("schema applied; seeding (about a minute)...", flush=True)
    t = time.perf_counter()
    subprocess.run([sys.executable, str(ROOT / "02_sql" / "seed.py"), dsn()], check=True)
    print(f"done in {time.perf_counter() - t:.0f}s")


def cmd_gen_data(a) -> None:
    kit = ROOT / "03_python" / "screen_rebuild" / "make_data.py"
    if a.big:
        # make_data.py always rewrites the small files too. On Windows they come out with different
        # line endings (same content), so keep the committed copies byte-for-byte.
        small = [kit.parent / "data" / n for n in ("transactions.csv", "products.sql", "products.db")]
        saved = {p: p.read_bytes() for p in small if p.exists()}
        try:
            subprocess.run([sys.executable, str(kit), "--big", str(a.big)], check=True)
        finally:
            for p, b in saved.items():
                p.write_bytes(b)
    for gen in sorted((ROOT / "03_python" / "data_tasks").glob("*/gen_data.py")):
        args = [sys.executable, str(gen)]
        if a.big_mb and "--size-mb" in gen.read_text():
            args += ["--size-mb", str(a.big_mb)]
        print(f"{gen.parent.name}: ", end="", flush=True)
        subprocess.run(args, check=True, cwd=gen.parent)
    if not a.big:
        print("screen_rebuild: small data is committed; use --big N for the large streaming file")


def cmd_check_sql(a) -> None:
    base, stem = find_problem(a.id)
    sol = Path(a.file) if a.file else base / "solutions" / f"{stem}.sql"
    expected = read_expected(base / "expected" / f"{stem}.sha256")
    with connect() as conn:
        t = time.perf_counter()
        rows = run_query(sol.read_text(), conn)
        ms = (time.perf_counter() - t) * 1000
    got = digest(rows)
    if got["sha256"] == expected["sha256"]:
        print(f"PASS  {stem}  ({got['rows']} rows, {ms:.0f} ms)")
        return
    print(f"FAIL  {stem}")
    print(f"  rows:    got {got['rows']:>8}   expected {expected['rows']}")
    print(f"  columns: got {got['columns']:>8}   expected {expected['columns']}")
    if got["columns"] == expected["columns"]:
        bad = [str(i + 1) for i, (g, e) in enumerate(zip(got["column_hashes"].split(","),
                                                         expected["column_hashes"].split(","))) if g != e]
        print(f"  columns whose values differ: {', '.join(bad) if bad else 'none (rows pair up differently)'}")
    sys.exit(1)


def cmd_hash_sql(a) -> None:
    with connect() as conn:
        rows = run_query(Path(a.file).read_text(), conn)
    for k, v in digest(rows).items():
        print(f"{k}: {v}")


def explain_and_time(conn, sql: str, runs: int) -> tuple[str, float]:
    sql = sql.strip().rstrip(";")
    conn.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT_S}s'")
    plan = "\n".join(r[0] for r in conn.execute(f"EXPLAIN (ANALYZE, BUFFERS) {sql}").fetchall())
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        conn.execute(sql).fetchall()
        times.append((time.perf_counter() - t) * 1000)
    return plan, statistics.median(times)


def cmd_time_sql(a) -> None:
    with connect() as conn:
        plan, ms = explain_and_time(conn, Path(a.file).read_text(), a.runs)
    print(plan)
    print(f"\nmedian of {a.runs} runs: {ms:,.1f} ms")


def user_indexes(conn) -> list[str]:
    return [r[0] for r in conn.execute(
        """SELECT i.indexname FROM pg_indexes i
           JOIN pg_index x ON x.indexrelid = (quote_ident(i.schemaname)||'.'||quote_ident(i.indexname))::regclass
           WHERE i.schemaname = 'public' AND i.tablename = ANY(%s) AND NOT x.indisprimary""",
        (list(TABLES),)).fetchall()]


def cmd_drop_indexes(a) -> None:
    with connect() as conn:
        names = user_indexes(conn)
        for n in names:
            conn.execute(f'DROP INDEX IF EXISTS "{n}"')
        conn.execute("ANALYZE")
    print(f"dropped {len(names)} index(es): {', '.join(names) or '-'}")


def cmd_perf(a) -> None:
    base, stem = find_problem(a.id)
    sol_dir = base / "solutions"
    slow = (sol_dir / f"{stem}.slow.sql").read_text()
    fast = (sol_dir / f"{stem}.sql").read_text()
    ddl = (sol_dir / f"{stem}.indexes.sql").read_text()
    expected = read_expected(base / "expected" / f"{stem}.sha256")
    if all(not ln.strip() or ln.strip().startswith("--") for ln in fast.splitlines()):
        sys.exit(f"{stem}.sql is empty. Write your rewrite first.")
    report = [f"# {stem} timing report ({datetime.now():%Y-%m-%d %H:%M})", ""]
    with connect() as conn:
        for n in user_indexes(conn):
            conn.execute(f'DROP INDEX IF EXISTS "{n}"')
        print("1/4 slow query, no secondary indexes ...", flush=True)
        p0, t0 = explain_and_time(conn, slow, a.runs)
        print("2/4 your rewrite, no secondary indexes ...", flush=True)
        p1, t1 = explain_and_time(conn, fast, a.runs)
        if ddl.strip():
            conn.execute(ddl)
            conn.execute("VACUUM ANALYZE")
        print("3/4 slow query + your indexes ...", flush=True)
        p2, t2 = explain_and_time(conn, slow, a.runs)
        print("4/4 your rewrite + your indexes ...", flush=True)
        p3, t3 = explain_and_time(conn, fast, a.runs)
        ok = digest(run_query(fast, conn))["sha256"] == expected["sha256"]
        if not a.keep_indexes:
            for n in user_indexes(conn):
                conn.execute(f'DROP INDEX IF EXISTS "{n}"')
    rows = [("slow query, no indexes", t0, p0), ("your rewrite, no indexes", t1, p1),
            ("slow query + your indexes", t2, p2), ("your rewrite + your indexes", t3, p3)]
    report += ["| Variant | Median ms | Speedup |", "|---|---:|---:|"]
    report += [f"| {name} | {t:,.1f} | {t0 / t:,.1f}x |" for name, t, _ in rows]
    report += ["", f"Rewrite returns the same result as the slow query: {'YES' if ok else 'NO'}", ""]
    for name, _, plan in rows:
        report += [f"## Plan: {name}", "```", plan, "```", ""]
    out = sol_dir / f"{stem}.report.md"
    out.write_text("\n".join(report))
    print("\n".join(report[2:10]))
    print(f"\nPlans written to {out.relative_to(ROOT)}. Now write your explanation in {stem}.answer.md.")
    if not ok:
        sys.exit(1)


def pytest_folder(folder: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "pytest", str(folder), "-q", "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    last = [ln for ln in p.stdout.strip().splitlines() if ln.strip()]
    summary = last[-1] if last else p.stderr.strip()[-200:]
    return p.returncode, summary.strip("= ")


def cmd_test(a) -> None:
    py = ROOT / "03_python"
    areas = {
        "screen": [py / "screen_rebuild"],
        "debugging": sorted(p for p in (py / "debugging").iterdir() if p.is_dir()),
        "data": sorted(p for p in (py / "data_tasks").iterdir() if p.is_dir()),
        "mock": sorted(p for p in (ROOT / "mock" / "python").glob("*/*") if p.is_dir()),
    }
    folders = (areas["screen"] + areas["debugging"] + areas["data"]) if a.area == "all" else areas[a.area]
    if a.which:
        folders = [f for f in folders if f.name.lower().startswith(a.which.lower().zfill(2))
                   or f.name.lower().startswith(a.which.lower())]
    failed = 0
    for f in folders:
        code, summary = pytest_folder(f)
        status = {0: "PASS", 5: "NO TESTS"}.get(code, "FAIL")
        failed += status == "FAIL"
        print(f"{status:<9} {f.relative_to(ROOT).as_posix():<48} {summary}")
    if a.verbose and folders:
        subprocess.run([sys.executable, "-m", "pytest", str(folders[0]), "-p", "no:cacheprovider"])
    sys.exit(1 if failed else 0)


def cmd_bench(a) -> None:
    hits = sorted((ROOT / "03_python" / "debugging").glob(f"{a.id.zfill(2)}_*/bench.py"))
    if not hits:
        sys.exit(f"No bench.py for exercise {a.id}")
    subprocess.run([sys.executable, str(hits[0])], cwd=hits[0].parent, check=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup-db").set_defaults(fn=cmd_setup_db)
    g = sub.add_parser("gen-data")
    g.add_argument("--big", type=int, help="rows for screen_rebuild/data/transactions_big.csv")
    g.add_argument("--big-mb", type=int, help="size of the data task 03 streaming file in MB")
    g.set_defaults(fn=cmd_gen_data)
    c = sub.add_parser("check-sql")
    c.add_argument("id")
    c.add_argument("--file", help="check a different .sql file")
    c.set_defaults(fn=cmd_check_sql)
    h = sub.add_parser("hash-sql")
    h.add_argument("file")
    h.set_defaults(fn=cmd_hash_sql)
    t = sub.add_parser("time-sql")
    t.add_argument("file")
    t.add_argument("--runs", type=int, default=3)
    t.set_defaults(fn=cmd_time_sql)
    p = sub.add_parser("perf")
    p.add_argument("id")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--keep-indexes", action="store_true")
    p.set_defaults(fn=cmd_perf)
    sub.add_parser("drop-indexes").set_defaults(fn=cmd_drop_indexes)
    te = sub.add_parser("test")
    te.add_argument("area", choices=["screen", "debugging", "data", "mock", "all"])
    te.add_argument("which", nargs="?", help="exercise number prefix, e.g. 03")
    te.add_argument("-v", "--verbose", action="store_true", help="also show full pytest output for the first match")
    te.set_defaults(fn=cmd_test)
    b = sub.add_parser("bench")
    b.add_argument("id")
    b.set_defaults(fn=cmd_bench)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
