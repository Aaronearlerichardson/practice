"""Task runner for the practice repo. Works the same in PowerShell, cmd, and bash.

Every sitting:
    python tasks.py next                     the one block to do now (starts its clock)
    python tasks.py done [ID]                tick it off (defaults to the block you're on)
    python tasks.py done --partial "left"    timebox hit at ~65%: tick it, queue the rest as a small block
    python tasks.py timer                    live countdown for the current block, with a beep
    python tasks.py status                   solved count, streak, XP and badges
    python tasks.py board                    open your board: study plan, calendar, badges (updates live)
    python tasks.py save ["message"]         commit and push now (most commands already do this)
    python tasks.py set-interview 2026-10-15 [...]
                                             the day of: review only. The day before: blocks dated
                                             for that day (@YYYY-MM-DD) first, then review only

Exercises:
    python tasks.py setup-db                 create the `practice` database, schema, and ~1.5M lab rows
    python tasks.py gen-data [--big N] [--big-mb MB]
                                             regenerate the file-based exercise data
    python tasks.py check-sql 03             check 02_sql/solutions/03_*.sql against its hash
    python tasks.py try-sql 03 [--reset]     run 03_*.sql on the Example's input rows from 02_sql/try/03_*.txt
                                             (edit them to see what changes), loaded into schema try_03
    python tasks.py perf 13                  time a performance problem before and after your fix
    python tasks.py time-sql FILE            print EXPLAIN (ANALYZE, BUFFERS) and the median runtime of one query
                                             (perf and time-sql also save plans to 02_sql/plans/ for the
                                             PostgreSQL extension's Visualize Query Plan from Editor)
    python tasks.py drop-indexes             remove every non-primary-key index you created
    python tasks.py test debugging [03]      run tests (areas: screen, debugging, data, mock, all)
    python tasks.py bench 05                 run a debugging exercise's benchmark
    python tasks.py hash-sql FILE            print the hash of a query result (used to build expected/)

Database connection: set PRACTICE_DSN, e.g. in PowerShell
    $env:PRACTICE_DSN = "postgresql://postgres:leet@localhost:5432/practice"
The default below matches the local `leetpg` Docker container.

Autosave: check-sql, try-sql, perf, time-sql, test, bench, next, done, status, timer and save commit everything
(your answers and coach/) and push it, so a wiped laptop never costs work again. Pushing is fail-soft.
Set PRACTICE_AUTOSAVE=0 to turn it off.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import textwrap
import time
import webbrowser
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DSN = "postgresql://postgres:leet@localhost:5432/practice"
SQL_DIRS = {"": ROOT / "02_sql", "m": ROOT / "mock" / "sql"}
TABLES = ("sites", "patients", "enrollments", "encounters", "quarterly_loads", "labs")
STATEMENT_TIMEOUT_S = 300

QUEUE = ROOT / "00_plan" / "queue.md"
INTERVIEWS = ROOT / "00_plan" / "interviews.txt"
COACH = ROOT / "coach"                       # the ADHD study coach's files; tasks.py only appends blocks-done.jsonl
BLOCKS_LOG = COACH / "blocks-done.jsonl"
STATE = ROOT / ".practice_state.json"        # gitignored: the block you're on, its clock, badges already announced
BOARD = ROOT / "board"                       # board/index.html reads board/data.js, which every command rewrites
PLANS = ROOT / "02_sql" / "plans"            # gitignored: EXPLAIN plans from perf and time-sql
SITTING_BLOCKS = 2                           # warm-up plus this many blocks is a full sitting
SITTING_GAP = timedelta(minutes=60)          # ticks closer together than this are one sitting
WARMUP_XP = 10                               # a coach warm-up; a block is worth its timebox in minutes
BIG_FILE_MB = 20                             # autosave never commits a file bigger than this
STRANDS = {"sql": "SQL", "lc": "SQL", "debug": "Python", "data": "Python", "screen": "Python",
           "design": "Design", "notes": "Design", "mpp": "Design", "story": "Stories", "mock": "Mock"}
TICKED: list[str] = []                       # blocks ticked during this command, for the autosave message


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


def run_query(sql: str, conn, read_only: bool = True, names: bool = False):
    """The rows of the last statement that returns any; with names=True, (column names, rows)."""
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
                cols, rows = [c.name for c in cur.description], cur.fetchall()
            if not cur.nextset():
                break
        if read_only:
            cur.execute("ROLLBACK")
    if rows is None:
        sys.exit("The file ran but returned no result set (is the last statement a SELECT?).")
    return (cols, rows) if names else rows


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
        if exists and a.if_missing:
            with connect() as conn:
                if conn.execute("SELECT to_regclass('public.labs') IS NOT NULL").fetchone()[0] and \
                        conn.execute("SELECT EXISTS (SELECT 1 FROM labs)").fetchone()[0]:
                    print(f"database {name} is already seeded")
                    return
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
        print(f"{paint('PASS', 'bold', 'green')}  {stem}  ({got['rows']} rows, {ms:.0f} ms)")
        tick(f"sql-{stem.split('_')[0]}", "pass")
        return
    print(f"{paint('FAIL', 'bold', 'red')}  {stem}  {paint('Wrong Answer', 'red')}")
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


# ----------------------------------------------------------------------------- try-sql: a problem's Example in a schema

HEADING_RE = re.compile(r"^(?:Input `(\w+)`|Output\b)")
TRY_ROWS = 30                                # try-sql prints at most this many result rows


def cell_value(c: str) -> str | None:
    """One cell as the problems write it: NULL (or a blank cell) is SQL NULL, '' the empty string, 'x' is x."""
    if not c or c.upper() == "NULL":
        return None
    return c[1:-1].replace("''", "'") if len(c) > 1 and c[0] == c[-1] == "'" else c


def cell_text(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))  # like Postgres: percentile_cont's 115.0 prints as 115
    return "''" if v == "" else str(v)


def read_tables(text: str, where: str) -> list[tuple[str, str, list[str], list[tuple]]]:
    """(table, heading, header, rows) for each "Input `table`" or "Output" heading and the ASCII table under it
    (table is "" for Output). Cells are split on |, so the columns don't have to line up."""
    out: list = []
    for n, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if m := HEADING_RE.match(s):
            out.append((m.group(1) or "", s, [], []))
        elif s.startswith("|") and out:
            _, _, header, rows = out[-1]
            cells = [c.strip() for c in s[1:].removesuffix("|").split("|")]
            if not header:
                header += cells
            elif len(cells) != len(header):
                sys.exit(f"{where} line {n}: {len(cells)} values for {len(header)} columns ({', '.join(header)}).")
            else:
                rows.append(tuple(map(cell_value, cells)))
    return out


def ascii_table(header: list[str], rows: list[tuple]) -> str:
    cells = [header] + [[cell_text(v) for v in r] for r in rows]
    w = [max(len(r[i]) for r in cells) for i in range(len(header))]
    rule = "+" + "+".join("-" * (n + 2) for n in w) + "+"
    line = lambda r: "| " + " | ".join(c.ljust(n) for c, n in zip(r, w)) + " |"  # noqa: E731
    return "\n".join([rule, line(cells[0]), rule, *map(line, cells[1:]), rule])


def loose(v) -> str:
    """norm(), and text that reads as a number compares as one, so the Example's '115' matches a float 115.0."""
    s = norm(v)
    try:
        return norm(Decimal(s))
    except InvalidOperation:
        return s


def load_try_schema(conn, schema: str, tables: list, where: str) -> None:
    """Drop and rebuild `schema` from the file: each table gets every column of the public one, no constraints."""
    import psycopg

    with conn.transaction():  # a row that doesn't load leaves the previous schema as it was
        conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.execute(f"CREATE SCHEMA {schema}")
        for t, _, header, rows in tables:
            if t not in TABLES:
                sys.exit(f"{where}: there is no table `{t}`. The tables are {', '.join(TABLES)}.")
            types = dict(conn.execute(
                "SELECT attname, format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped ORDER BY attnum",
                (f"public.{t}",)).fetchall())
            if bad := [c for c in header if c not in types]:
                sys.exit(f"{where}: `{t}` has no column {', '.join(bad)}. Its columns are {', '.join(types)}.")
            conn.execute(f"CREATE TABLE IF NOT EXISTS {schema}.{t} "
                         f"({', '.join(f'{c} {ty}' for c, ty in types.items())})")
            insert = f"INSERT INTO {schema}.{t} ({', '.join(header)}) VALUES ({', '.join(['%s'] * len(header))})"
            for r in rows:
                try:
                    conn.execute(insert, r)
                except psycopg.Error as e:
                    sys.exit(f"{where}: this `{t}` row doesn't load ({e.diag.message_primary}):\n"
                             f"  | {' | '.join(map(cell_text, r))} |")


def cmd_try_sql(a) -> None:
    import psycopg

    base, stem = find_problem(a.id)
    num = stem.split("_")[0]
    md = (base / "problems" / f"{stem}.md").read_text(encoding="latin-1")
    sec = re.search(r"^## Example\b(.*?)(?=^## |\Z)", md, re.S | re.M)
    example = read_tables(sec.group(1), f"{stem}.md") if sec else []
    inputs, output = [t for t in example if t[0]], next((t for t in example if not t[0]), None)
    if not inputs:
        sys.exit(f"{stem} has no Example input to try.")
    path, schema = base / "try" / f"{stem}.txt", f"try_{num}"
    rel = path.relative_to(ROOT).as_posix()
    if a.reset or not path.exists():
        lines = [f"Example input for {stem}, copied from its problem. Edit it, then: python tasks.py try-sql {num}",
                 "Change values, copy a row and tweak it, or delete rows. The columns don't have to line up.",
                 "NULL is SQL NULL, '' is the empty string, and a column a table doesn't show is NULL.",
                 f"Back to the Example: python tasks.py try-sql {num} --reset", ""]
        for _, heading, header, rows in inputs:
            lines += [heading, "", ascii_table(header, rows), ""]
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"{'Reset' if a.reset else 'Wrote'} {rel} from the Example. Edit its rows, then run this again.\n")
    tables = [t for t in read_tables(path.read_text(encoding="utf-8"), rel) if t[0]]
    sol = Path(a.file) if a.file else base / "solutions" / f"{stem}.sql"
    with connect() as conn:
        load_try_schema(conn, schema, tables, rel)
        print(f"{schema}: " + ", ".join(f"{t} ({len(r)} row{'s' if len(r) != 1 else ''})" for t, _, _, r in tables)
              + f".  To query it yourself in VS Code: SET search_path TO {schema};")
        conn.execute(f"SET search_path TO {schema}")  # not public, so a table the file doesn't have is an error
        try:
            cols, got = run_query(sol.read_text(), conn, names=True)
        except psycopg.Error as e:
            sys.exit(f"Your query failed on {schema}, which has only {', '.join(t for t, *_ in tables)} (another "
                     f"table needs its own Input `name` block in {rel}):\n{e}")
    print(f"\nYour query ({sol.name}) on {rel}:")
    print(ascii_table(cols, got[:TRY_ROWS]))
    more = f"; the first {TRY_ROWS} shown" if len(got) > TRY_ROWS else ""
    print(f"({len(got)} row{'s' if len(got) != 1 else ''}{more})")
    if output is None:
        return
    if {t: (tuple(h), Counter(r)) for t, _, h, r in tables} != {t: (tuple(h), Counter(r)) for t, _, h, r in inputs}:
        print(paint("The input is edited, so there's no Example output to compare with.", "dim"))
        return
    _, heading, want_cols, want = output
    if note := re.search(r"\((.*)\)", heading):  # "Output (this example uses ...)": it shows only some rows
        keys = {loose(r[0]) for r in want}
        got = [r for r in got if loose(r[0]) in keys]
        print(paint(f"The Example output shows only some rows ({note.group(1)}), so only your rows with a "
                    f"{want_cols[0]} in it are compared.", "dim"))
    if len(cols) == len(want_cols) and \
            sorted(tuple(map(loose, r)) for r in got) == sorted(tuple(map(loose, r)) for r in want):
        print(paint(f"{glyph('✓', '+')} Matches the Example output", "bold", "green"))
        return
    print(paint(f"{glyph('✗', 'x')} Not the Example output yet.", "bold", "red")
          + " Expected (row order and column names don't matter, column order does):")
    print(ascii_table(want_cols, want))


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


def save_plan(name: str, plan: str) -> Path:
    PLANS.mkdir(parents=True, exist_ok=True)
    out = PLANS / f"{name}.txt"
    out.write_text(plan + "\n", encoding="utf-8")
    return out


def plan_tip(path: Path) -> str:
    return (f"See it as a graph: open {path.relative_to(ROOT).as_posix()} in VS Code, then Ctrl+Shift+P > "
            "PGSQL: Visualize Query Plan from Editor.")


def cmd_time_sql(a) -> None:
    with connect() as conn:
        plan, ms = explain_and_time(conn, Path(a.file).read_text(), a.runs)
    print(plan)
    print(f"\nmedian of {a.runs} runs: {ms:,.1f} ms")
    print(plan_tip(save_plan(Path(a.file).stem, plan)))


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
    saved = [save_plan(f"{stem}.{n}", plan) for n, (_, _, plan) in
             zip(("1-slow", "2-rewrite", "3-slow-indexed", "4-rewrite-indexed"), rows)]
    print(plan_tip(saved[-1]) + " The other three variants are next to it.")
    if not ok:
        sys.exit(1)
    tick(f"sql-{stem.split('_')[0]}", "pass")


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
    prefix = {"debugging": "debug", "data": "data"}.get(a.area)
    failed = 0
    for f in folders:
        code, summary = pytest_folder(f)
        status = {0: "PASS", 5: "NO TESTS"}.get(code, "FAIL")
        failed += status == "FAIL"
        shown = paint(f"{status:<9}", "bold", {"PASS": "green", "FAIL": "red"}.get(status, "dim"))
        print(f"{shown} {f.relative_to(ROOT).as_posix():<48} {summary}")
        if status == "PASS" and prefix and f.parent.parent.name == "03_python":
            tick(f"{prefix}-{f.name.split('_')[0]}", "pass")
    if a.verbose and folders:
        subprocess.run([sys.executable, "-m", "pytest", str(folders[0]), "-p", "no:cacheprovider"])
    sys.exit(1 if failed else 0)


def cmd_bench(a) -> None:
    hits = sorted((ROOT / "03_python" / "debugging").glob(f"{a.id.zfill(2)}_*/bench.py"))
    if not hits:
        sys.exit(f"No bench.py for exercise {a.id}")
    subprocess.run([sys.executable, str(hits[0])], cwd=hits[0].parent, check=False)


# ----------------------------------------------------------------------------- the queue

BLOCK_RE = re.compile(r"^- \[([ xX])\] `([a-z0-9][a-z0-9-]*)`\s*(.*)$")
ANCHOR_RE = re.compile(r"\s*@(\d{4}-\d{2}-\d{2})")
MINUTES_RE = re.compile(r"\s*·\s*(\d+)\s*min\b")


def timebox(title: str) -> int:
    m = MINUTES_RE.search(title) or re.search(r"(\d+)\s*min", title)
    return int(m.group(1)) if m else 20


@dataclass
class Block:
    id: str
    done: bool
    line: int          # index into the queue file's lines
    title: str
    body: list[str]
    anchor: date | None  # `@YYYY-MM-DD`: hidden until that day, then first in line
    section: str = ""    # the `## ` heading it sits under

    @property
    def minutes(self) -> int:
        return timebox(self.title)

    @property
    def name(self) -> str:
        return MINUTES_RE.sub("", self.title).strip()

    @property
    def strand(self) -> str:
        return STRANDS.get(self.id.split("-")[0], "Other")

    def show(self) -> str:
        return "\n".join([f"{self.id}  {self.title}"] + [f"  {ln}" for ln in self.body])


def plain(md: str) -> str:
    return md.replace("**", "").replace("`", "").strip()


def read_queue() -> tuple[list[str], str, list[Block]]:
    raw = QUEUE.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    blocks = []
    section = ""
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            section = ln[3:].strip()
        m = BLOCK_RE.match(ln)
        if not m:
            continue
        body = []
        for nxt in lines[i + 1:]:
            if not nxt.startswith("  ") or not nxt.strip():
                break
            body.append(plain(nxt))
        anchor = ANCHOR_RE.search(m.group(3))
        blocks.append(Block(m.group(2), m.group(1) != " ", i, plain(ANCHOR_RE.sub("", m.group(3))), body,
                            date.fromisoformat(anchor.group(1)) if anchor else None, section))
    return lines, nl, blocks


def pending(blocks: list[Block], today: date) -> list[Block]:
    todo = [b for b in blocks if not b.done and (b.anchor is None or b.anchor <= today)]
    return sorted(todo, key=lambda b: b.anchor is None)  # stable sort: dated blocks first, then file order


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return [e for e in out if isinstance(e, dict)]


def due_reviews(today: date) -> list[str]:
    """Topics the coach has due, read-only. The coach is the only writer of its schedule."""
    data = load_json(COACH / "review-schedule.json", [])
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), [])
    return [str(it.get("topic", "?")) for it in data if isinstance(it, dict)
            and str(it.get("dueDate", "9999-12-31")) <= today.isoformat()]


def interview_dates() -> list[date]:
    out = set()
    try:
        lines = INTERVIEWS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for ln in lines:
        try:
            out.add(date.fromisoformat(ln.split("#")[0].strip()))
        except ValueError:
            pass
    return sorted(out)


def tick(bid: str, result: str = "done", left: str | None = None) -> bool:
    """Check a block off in queue.md and log it for the coach. A pass also clears that block's leftovers."""
    if not QUEUE.exists():
        return False
    lines, nl, blocks = read_queue()
    rest = re.compile(re.escape(bid) + r"-rest\d*")
    hits = [b for b in blocks if not b.done and (b.id == bid or (result == "pass" and rest.fullmatch(b.id)))]
    if not hits:
        return False
    state = load_json(STATE, {})
    now = datetime.now()
    for b in hits:
        lines[b.line] = lines[b.line].replace("- [ ]", "- [x]", 1)
        minutes = None
        if state.get("block") == b.id:
            minutes = round((now - datetime.fromisoformat(state["started"])).total_seconds() / 60)
            save_state(block=None, started=None, minutes=None)
        COACH.mkdir(exist_ok=True)
        with BLOCKS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"date": now.date().isoformat(), "time": f"{now:%H:%M}", "block": b.id,
                                "title": b.title, "result": result, "minutes": minutes, "left": left}) + "\n")
        TICKED.append(b.id)
        print_accepted(b, minutes, result == "partial")
    if left:
        base = re.sub(r"-rest\d*$", "", bid)
        ids, rid, n = {b.id for b in blocks}, f"{base}-rest", 2
        while rid in ids:
            rid, n = f"{base}-rest{n}", n + 1
        at = next((i for i, ln in enumerate(lines) if ln.startswith("## Bonus")), len(lines))
        while at > 0 and not lines[at - 1].strip():
            at -= 1
        name = re.sub(r"^Finish: ", "", hits[0].title.split(" · ")[0])
        gap = [] if lines[at - 1].startswith(("- [", "  ")) else [""]
        lines[at:at] = gap + [f"- [ ] `{rid}` **Finish: {name}** · 10 min", f"  What's left: {left}"]
        print(f"Queued the rest as {rid} (10 min), under Leftovers.")
    QUEUE.write_bytes((nl.join(lines) + nl).encode("utf-8"))
    return True


def report_progress() -> None:
    p = progress()
    n = p["days"].get(p["today"], {}).get("blocks", 0)
    before = n - len(TICKED)
    streak = streak_text(p)
    line = f"{streak}  ·  {p['xp']} XP  ·  {n} block{'s' if n != 1 else ''} today  ·  {p['solved']}/{p['total']} solved"
    print("\n" + (paint(line, "bold", "yellow") if before == 0 and p["streak"] else line))
    announce_badges(p)
    nb = next_badge(p)
    if nb:
        print(paint(f"Next badge: {nb['name']} {nb['n']}/{nb['goal']} ({nb['how']})", "dim"))
    if before // SITTING_BLOCKS < n // SITTING_BLOCKS:
        print("That's a full sitting. Wrap up: tell Claude \"I'm done for today\" (about 5 min with the coach).")
        print("Still in flow? python tasks.py next")
    else:
        print("Next: python tasks.py next")


def interview_near(today: date) -> date | None:
    """An interview today or tomorrow."""
    return next((d for d in interview_dates() if d - timedelta(days=1) <= today <= d), None)


REVIEW_LIST = [
    "Reread your five stories (01_cross_functional/stories.md). Tell two out loud, 2 min each.",
    "Reread the red flags in 04_system_design/rubric.md and the minute budget in template.md.",
    "Reread your perf answers: the 3 sentences at the end of 02_sql/perf_lab.sql, "
    "and 02_sql/solutions/13_*.answer.md and 14_*.answer.md.",
    "A short warm-up with the coach is fine (\"let's study\"). Then stop for the day.",
]


def print_review_list(d: date, today: date) -> None:
    when = "today" if d == today else f"tomorrow ({d:%a %b %d})"
    print(f"Interview {when}: nothing new. This is the whole list:\n")
    for i, item in enumerate(REVIEW_LIST, 1):
        print(textwrap.fill(item, 100, initial_indent=f"  {i}. ", subsequent_indent="     "))


def what_next(today: date, skip_warmup: bool = False) -> tuple[str, object]:
    """What `next` would show, without starting anything: ("review", interview date), ("warmup", due topics),
    ("block", Block) or ("empty", None)."""
    _, _, blocks = read_queue()
    todo = pending(blocks, today)
    d = interview_near(today)
    if d is not None:
        # Review only, except blocks dated for today: the day before (like the mock's gap blocks) or the morning
        # of (a warm-up set before the interview).
        todo = [b for b in todo if b.anchor == today]
        if not todo:
            return "review", d
    due = due_reviews(today)
    warmed_up = any(e.get("date") == today.isoformat() for e in jsonl(COACH / "sessions.log.jsonl"))
    if due and not warmed_up and not skip_warmup:
        return "warmup", due
    return ("block", todo[0]) if todo else ("empty", None)


def save_state(**changes) -> None:
    """Merge into .practice_state.json; a None value removes that key."""
    state = load_json(STATE, {})
    state.update(changes)
    STATE.write_text(json.dumps({k: v for k, v in state.items() if v is not None}), encoding="utf-8")


def cmd_next(a) -> None:
    today = date.today()
    kind, x = what_next(today, a.skip_warmup)
    if kind == "review":
        print_review_list(x, today)
        return
    if kind == "warmup":
        print(f"Warm-up first: {len(x)} review{'s' if len(x) != 1 else ''} due ({', '.join(x)}).")
        print("Tell Claude \"let's study\". The ADHD study coach runs it, about 5-10 min.")
        print("Then run python tasks.py next again.  (No Claude handy? python tasks.py next --skip-warmup)")
        return
    if kind == "empty":
        print("The queue is empty. Redo a SQL problem that felt shaky, or add blocks to 00_plan/queue.md.")
        return
    b = x
    state = load_json(STATE, {})
    now = datetime.now()
    started = datetime.fromisoformat(state["started"]) if state.get("block") == b.id else None
    back = started is not None and now - started > timedelta(minutes=b.minutes)
    if started is None or back:
        started = now
        save_state(block=b.id, started=now.isoformat(timespec="seconds"), minutes=b.minutes)
    if back:
        print(paint("Welcome back.", "bold", "cyan") + f" You're still on {b.id}. Here's a fresh {b.minutes}-min clock.\n")
    print(b.show())
    if not any("ticks" in ln for ln in b.body):
        print("  When it's done: python tasks.py done")
    print(f"\nClock: {b.minutes} min, until {started + timedelta(minutes=b.minutes):%H:%M}."
          "  Countdown with a beep: python tasks.py timer")


def cmd_done(a) -> None:
    lines, nl, blocks = read_queue()
    bid = a.id or load_json(STATE, {}).get("block") or next((b.id for b in pending(blocks, date.today())), None)
    if not bid:
        sys.exit("Nothing to tick: every block in 00_plan/queue.md is done.")
    b = next((b for b in blocks if b.id == bid), None)
    if b is None:
        close = [x.id for x in blocks if bid and bid.split("-")[0] in x.id][:8]
        sys.exit(f"No block '{bid}' in 00_plan/queue.md." + (f" Did you mean: {', '.join(close)}?" if close else ""))
    if a.undo:
        if b.done:
            lines[b.line] = re.sub(r"^- \[[xX]\]", "- [ ]", lines[b.line])
            QUEUE.write_bytes((nl.join(lines) + nl).encode("utf-8"))
        print(f"[ ] {b.id} is open again.")
        return
    if b.done:
        print(f"{b.id} is already done.")
        return
    tick(b.id, "partial" if a.partial else "done", a.partial)


def beep(times: int) -> None:
    for _ in range(times):
        try:
            import winsound
            winsound.Beep(880, 250)
        except (ImportError, RuntimeError):
            print("\a", end="", flush=True)
            time.sleep(0.25)


def cmd_timer(a) -> None:
    state = load_json(STATE, {})
    if a.minutes:
        label, start, minutes = "timer", datetime.now(), a.minutes
    elif state.get("block"):
        label, start, minutes = state["block"], datetime.fromisoformat(state["started"]), state["minutes"]
    else:
        sys.exit("No block is running. python tasks.py next starts one, or: python tasks.py timer 15")
    end = start + timedelta(minutes=minutes)
    half = start + (end - start) / 2
    said_half = datetime.now() >= half
    print(f"{label}: until {end:%H:%M}. Ctrl+C stops the timer, not your work.")
    try:
        while (left := end - datetime.now()).total_seconds() > 0:
            if not said_half and datetime.now() >= half:
                said_half = True
                beep(1)
                print("\rHalfway. Say out loud, in one sentence, where you are.      ")
            m, s = divmod(int(left.total_seconds()), 60)
            print(f"\r  {m:2d}:{s:02d} left ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTimer stopped.")
        return
    beep(3)
    print("\rTime.            ")
    print("Done?                 python tasks.py done")
    print("Mostly there (~65%)?  python tasks.py done --partial \"what's left\"   (that counts as done)")


def bar(n: int, m: int, width: int = 12) -> str:
    fill = round(width * n / m) if m else 0
    return paint(glyph("█", "#") * fill, "green") + paint(glyph("░", "-") * (width - fill), "dim")


def cmd_status(a) -> None:
    today = date.today()
    p = progress(today)
    bonus = f" (+{p['bonus_solved']} bonus)" if p["bonus_solved"] else ""
    days = p["study_days"]
    print(paint(f"{p['solved']}/{p['total']} solved{bonus}", "bold") + f"  ·  {streak_text(p)}  ·  {p['xp']} XP"
          f"  ·  {days} study day{'s' if days != 1 else ''}")
    print("  " + "   ".join(paint(f"{SIZES[k][0]} {n}/{m}", SIZES[k][1]) for k, (n, m) in p["by_size"].items()))
    print()
    for strand, (n, m) in p["by_strand"].items():
        print(f"  {strand:<8} {bar(n, m)} {n}/{m}")
    earned = [b["name"] for b in p["badges"] if b["earned"]]
    print(f"\nBadges {len(earned)}/{len(p['badges'])}: {', '.join(earned) or 'none yet'}")
    nb = next_badge(p)
    if nb:
        print(f"Next badge: {nb['name']} {nb['n']}/{nb['goal']} ({nb['how']})")
    n = p["days"].get(p["today"], {}).get("blocks", 0)
    print(f"\nToday: {n} block{'s' if n != 1 else ''}. Board: python tasks.py board")
    due = due_reviews(today)
    if due:
        print(f"Due with the coach: {', '.join(due)}")
    ahead = [d for d in interview_dates() if d >= today]
    if ahead:
        print("Interviews: " + ", ".join(f"{d:%a %b %d}" for d in ahead))


def cmd_set_interview(a) -> None:
    try:
        new = {date.fromisoformat(d) for d in a.dates}
    except ValueError as e:
        sys.exit(f"Use YYYY-MM-DD dates ({e}).")
    dates = sorted(new if a.clear else set(interview_dates()) | new)
    INTERVIEWS.write_text("# One interview date per line (YYYY-MM-DD). `python tasks.py set-interview` edits this.\n"
                          + "".join(f"{d}\n" for d in dates), encoding="utf-8")
    print("Interviews: " + (", ".join(f"{d:%a %b %d}" for d in dates) or "none"))
    print("On each one, python tasks.py next shows a review-only list. The day before, it shows blocks dated")
    print("for that day (@YYYY-MM-DD) first, then the same list.")


# ----------------------------------------------------------------------------- feedback: verdicts, streaks, XP, badges

SIZES = {"easy": ("Easy", "cyan"), "medium": ("Medium", "yellow"), "hard": ("Hard", "red")}  # by timebox
ANSI = {"bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33", "cyan": "36"}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DONE_ON_RE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (" + "|".join(MONTHS) + r") (\d{1,2})\b")
PATH_RE = re.compile(r"\b\d\d_[\w.-]+(?:/[\w.*-]+)+")
BADGE_SETS = [  # badges for finishing named blocks: (id, name, what earns it, tier, icon, block ids)
    ("storyteller", "Storyteller", "all five stories written from memory", "gold", "chat",
     ("story-1", "story-2", "story-3", "story-4", "story-5")),
    ("live-take", "Live Take", "all five stories told out loud, back to back", "silver", "mic", ("story-aloud",)),
    ("window-functions", "Window Functions", "SQL 01, 02 and 03 passed", "silver", "grid",
     ("sql-01", "sql-02", "sql-03")),
    ("plan-reader", "Plan Reader", "the slow-query answer, SQL 13 and its explanation", "gold", "plan",
     ("sql-slow-query", "sql-13", "sql-13-explain")),
    ("whiteboard", "Whiteboard", "design 01 as a speed round, then graded", "silver", "compass",
     ("design-01", "design-01-grade")),
    ("mock-day", "Mock Day", "all five parts of the mock", "gold", "flag",
     ("mock-1", "mock-2", "mock-3", "mock-4", "mock-5")),
]


def size(minutes: int) -> str:
    return "easy" if minutes <= 10 else "medium" if minutes <= 20 else "hard"


@functools.cache
def color_ok() -> bool:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":  # let the Windows console read ANSI colors
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h, mode = k.GetStdHandle(-11), ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                k.SetConsoleMode(h, mode.value | 4)
        except (AttributeError, OSError):
            pass
    return True


def paint(text: str, *styles: str) -> str:
    return f"\033[{';'.join(ANSI[s] for s in styles)}m{text}\033[0m" if color_ok() else text


def glyph(fancy: str, fallback: str) -> str:
    return fancy if (sys.stdout.encoding or "").lower().replace("-", "") == "utf8" else fallback


def print_accepted(b: Block, minutes: int | None, partial: bool) -> None:
    """The green verdict for a finished block."""
    print(paint(f"{glyph('✓', '+')} Accepted", "bold", "green") + f"   {b.id}  {b.name}")
    facts = ["65% counts"] if partial else []
    if minutes is not None:
        under = b.minutes - minutes
        facts.append(f"{minutes} min, {under} under the {b.minutes}-min timebox" if under > 0 else f"{minutes} min")
    print(paint("  " + "  ·  ".join(facts + [f"+{b.minutes} XP"]), "green"))


def iso_day(s) -> date | None:
    try:
        return date.fromisoformat(str(s))
    except ValueError:
        return None


def progress(today: date | None = None) -> dict:
    """Everything the verdicts, `status` and the board show, from queue.md, the block log and the coach's log."""
    today = today or date.today()
    _, _, blocks = read_queue()
    log, sessions = jsonl(BLOCKS_LOG), jsonl(COACH / "sessions.log.jsonl")
    done = {b.id for b in blocks if b.done}
    days: dict[str, dict] = {}

    def add(d, key: str) -> None:
        if iso_day(d):
            days.setdefault(str(d), {"blocks": 0, "warmups": 0})[key] += 1

    for e in log:
        add(e.get("date"), "blocks")
    logged = {e.get("block") for e in log}
    for b in blocks:  # blocks finished before the log existed carry their day in the title ("· Fri Oct 9")
        m = DONE_ON_RE.search(b.title)
        if b.done and b.id not in logged and m:
            add(date(today.year, MONTHS.index(m.group(1)) + 1, int(m.group(2))).isoformat(), "blocks")
    for s in sessions:
        add(s.get("date"), "warmups")
    active = sorted(d for d in map(iso_day, days) if d <= today)

    streak = best = 0
    for prev, d in zip([None] + active, active):
        streak = streak + 1 if prev and (d - prev).days <= 2 else 1  # one rest day between study days is fine
        best = max(best, streak)
    if not active or (today - active[-1]).days > 2:
        streak = 0

    sittings: dict[str, list[int]] = {}  # per day, blocks in each sitting
    last = None
    for e in log:
        try:
            t = datetime.fromisoformat(f"{e['date']}T{e['time']}")
        except (KeyError, TypeError, ValueError):
            continue
        day = sittings.setdefault(e["date"], [])
        if day and last and t - last < SITTING_GAP:
            day[-1] += 1
        else:
            day.append(1)
        last = t

    main = [b for b in blocks if b.section != "Bonus"]
    by_size = {k: [0, 0] for k in SIZES}
    by_strand: dict[str, list[int]] = {}
    for b in main:
        for bucket in (by_size[size(b.minutes)], by_strand.setdefault(b.strand, [0, 0])):
            bucket[0] += b.done
            bucket[1] += 1
    order = ["SQL", "Python", "Design", "Stories", "Mock"]
    by_strand = dict(sorted(by_strand.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99))

    n = len(done)
    under = any(isinstance(e.get("minutes"), int) and e["minutes"] <= timebox(str(e.get("title", ""))) for e in log)
    strands = {STRANDS.get(i.split("-")[0]) for i in done} & {"SQL", "Python", "Design", "Stories"}
    spec = [
        ("first-accepted", "First Accepted", "your first block finished", "bronze", "check", n, 1),
        ("five-down", "Five Down", "5 blocks finished", "bronze", "5", n, 5),
        ("double-digits", "Double Digits", "10 blocks finished", "silver", "10", n, 10),
        ("twenty", "Twenty", "20 blocks finished", "gold", "20", n, 20),
        ("warmed-up", "Warmed Up", "a warm-up with the coach", "bronze", "sun", len(sessions), 1),
        ("review-habit", "Review Habit", "3 warm-ups with the coach", "silver", "sun", len(sessions), 3),
        ("full-sitting", "Full Sitting", "2 blocks in one sitting", "bronze", "stack",
         max(map(max, sittings.values()), default=0), 2),
        ("second-wind", "Second Wind", "a second sitting on the same day", "silver", "repeat",
         max(map(len, sittings.values()), default=0), 2),
        ("comeback", "Comeback", "back at it after 2 or more days away", "bronze", "return",
         int(any((d - c).days >= 3 for c, d in zip(active, active[1:]))), 1),
        ("under-the-clock", "Under the Clock", "a block finished inside its timebox", "bronze", "clock", int(under), 1),
        ("counts", "65% Counts", "done --partial when the clock ran out", "bronze", "partial",
         int(any(e.get("result") == "partial" for e in log)), 1),
        ("clean-plate", "Clean Plate", "a leftover (-rest block) finished", "bronze", "plate",
         int(any(re.search(r"-rest\d*$", i) for i in done)), 1),
        ("on-a-roll", "On a Roll", "a 3-day streak", "silver", "flame", best, 3),
        ("five-days", "Five Study Days", "studied on 5 different days", "gold", "calendar", len(active), 5),
        ("all-rounder", "All-Rounder", "a block each in SQL, Python, Design and Stories", "gold", "quad",
         len(strands), 4),
        ("bug-hunter", "Bug Hunter", "3 debugging exercises fixed", "silver", "bug",
         sum(i.startswith("debug-") for i in done), 3),
    ]
    sets = list(BADGE_SETS)
    if interviews := interview_dates():
        eve = interviews[0] - timedelta(days=1)
        if dated := tuple(b.id for b in blocks if b.anchor == eve):
            sets.append(("final-stretch", "Final Stretch", f"every block dated {eve:%a %b} {eve.day}", "gold", "star",
                         dated))
    ids = {b.id for b in blocks}
    for bid, name, how, tier, icon, want in sets:
        if have := [i for i in want if i in ids]:
            spec.append((bid, name, how, tier, icon, sum(i in done for i in have), len(have)))
    badges = [{"id": i, "name": nm, "how": how, "tier": tier, "icon": icon, "n": min(k, goal), "goal": goal,
               "earned": k >= goal} for i, nm, how, tier, icon, k, goal in spec]

    return {"today": today.isoformat(), "days": days, "streak": streak, "best_streak": best,
            "studied_today": bool(active) and active[-1] == today, "study_days": len(active),
            "xp": sum(b.minutes for b in blocks if b.done) + WARMUP_XP * len(sessions),
            "solved": sum(b.done for b in main), "total": len(main),
            "bonus_solved": sum(b.done for b in blocks if b.section == "Bonus"),
            "by_size": by_size, "by_strand": by_strand, "badges": badges}


def streak_text(p: dict) -> str:
    flame, s = glyph("🔥", "*"), p["streak"]
    if not s:
        return f"{flame} a block today starts a streak"
    if p["studied_today"]:
        return f"{flame} {s}-day streak"
    return f"{flame} {s}-day streak (a block today makes it {s + 1})"


def next_badge(p: dict) -> dict | None:
    """The unearned badge you're closest to."""
    todo = [b for b in p["badges"] if not b["earned"]]
    return max(todo, key=lambda b: (b["n"] / b["goal"], -b["goal"]), default=None)


def announce_badges(p: dict) -> None:
    """Print badges earned since the last announcement (remembered in .practice_state.json)."""
    earned = [b for b in p["badges"] if b["earned"]]
    seen = set(load_json(STATE, {}).get("badges", []))
    new = [b for b in earned if b["id"] not in seen]
    for b in new:
        print(paint(f"{glyph('🏅', '*')} New badge: {b['name']}", "bold", "yellow") + f"  ({b['how']})")
    if new:
        save_state(badges=sorted(seen | {b["id"] for b in earned}))


def vscode_uri(f: Path) -> str:
    return "vscode://file/" + f.resolve().as_posix()


def block_json(b: Block) -> dict:
    files: list[Path] = []
    for raw in PATH_RE.findall(" ".join(b.body)):
        for f in sorted(ROOT.glob(raw.rstrip(".,;:")))[:1]:
            if f.is_file() and f not in files:
                files.append(f)
    if m := re.fullmatch(r"sql-(\d\d)", b.id):  # where the query goes, so the extension can run and plan it
        exp = sorted((ROOT / "02_sql" / "expected").glob(f"{m.group(1)}_*.sha256"))
        sol = ROOT / "02_sql" / "solutions" / f"{exp[0].stem}.sql" if exp else None
        if sol and sol.exists() and sol not in files:
            files.insert(1, sol)
    return {"id": b.id, "name": b.name, "minutes": b.minutes, "size": size(b.minutes), "strand": b.strand,
            "section": b.section, "done": b.done, "anchor": b.anchor.isoformat() if b.anchor else None,
            "body": b.body, "links": [{"name": f.name, "uri": vscode_uri(f)} for f in files[:4]]}


def write_board() -> None:
    """board/data.js: everything board/index.html shows. The open page picks up changes within seconds."""
    today = date.today()
    data = progress(today)
    _, _, blocks = read_queue()
    state = load_json(STATE, {})
    kind, x = what_next(today)
    live = next((b for b in blocks if b.id == state.get("block") and not b.done), None)
    if live and kind != "review":  # a block you've started stays on top, even with a warm-up due
        kind, x = "block", live
    pick: dict = {"kind": kind}
    if kind == "block":
        pick["id"] = x.id
    elif kind == "warmup":
        then_kind, then = what_next(today, skip_warmup=True)
        pick.update(due=x, then=then.id if then_kind == "block" else None)
    elif kind == "review":
        pick.update(date=x.isoformat(), items=REVIEW_LIST)
    plans = sorted(PLANS.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True) if PLANS.exists() else []
    data.update(
        blocks=[block_json(b) for b in blocks], pick=pick,
        current={k: state.get(k) for k in ("block", "started", "minutes")} if state.get("block") else None,
        recent=[{"date": e.get("date"), "time": e.get("time"), "block": e.get("block"), "result": e.get("result"),
                 "minutes": e.get("minutes"), "name": MINUTES_RE.sub("", str(e.get("title", ""))).strip()}
                for e in jsonl(BLOCKS_LOG)[-8:][::-1]],
        interviews=[d.isoformat() for d in interview_dates()], due=due_reviews(today),
        plans=[{"name": f.name, "uri": vscode_uri(f)} for f in plans[:6]],
    )
    body = json.dumps(data, ensure_ascii=False)
    BOARD.mkdir(exist_ok=True)
    (BOARD / "data.js").write_text(
        "// Written by tasks.py after every command. Don't edit.\n"
        f"window.BOARD = {body};\n"
        f"window.BOARD.version = \"{hashlib.sha1(body.encode()).hexdigest()[:12]}\";\n"
        f"window.BOARD.generated = \"{datetime.now():%Y-%m-%dT%H:%M:%S}\";\n"
        "if (window.onBoard) window.onBoard(window.BOARD);\n", encoding="utf-8")


def cmd_board(a) -> None:
    write_board()
    page = BOARD / "index.html"
    print(f"Board: {page.relative_to(ROOT).as_posix()}. Leave the tab open: it updates whenever tasks.py runs.")
    if not a.no_open:
        webbrowser.open(page.resolve().as_uri())


def extras(fn) -> None:
    """Badges and the board are extras: they never break a command."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        print(paint(f"(badges or board skipped: {e})", "dim"))


# ----------------------------------------------------------------------------- autosave

def git(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def autosave(reason: str, verbose: bool = False) -> None:
    """Commit everything and push. Never raises: a failed push still leaves a local commit."""
    if os.environ.get("PRACTICE_AUTOSAVE", "1") == "0":
        return
    try:
        branch = git("symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
        busy = [n for n in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply")
                if (ROOT / ".git" / n).exists()]
        if not branch or busy:
            print("Autosave skipped: finish the merge or rebase (or switch to a branch) first.")
            return
        git("add", "-A")
        for p in filter(None, git("diff", "--cached", "--name-only", "-z").stdout.split("\0")):
            f = ROOT / p
            if f.is_file() and f.stat().st_size > BIG_FILE_MB * 1024 * 1024:
                git("reset", "-q", "--", p)
                print(f"Autosave left out {p} (over {BIG_FILE_MB} MB). Add it to .gitignore.")
        committed = git("diff", "--cached", "--quiet").returncode != 0
        if committed:
            r = git("commit", "-q", "-m", f"autosave: {reason}")
            if r.returncode:
                print(f"Autosave couldn't commit: {(r.stderr or r.stdout).strip()}")
                return
        ahead = git("rev-list", "--count", "@{u}..HEAD")
        if not committed and ahead.returncode == 0 and ahead.stdout.strip() == "0":
            if verbose:
                print("Nothing new to save. GitHub is up to date.")
            return
        p = git("push", "-q", "-u", "origin", "HEAD", timeout=45)
        if p.returncode == 0:
            print("Saved to GitHub.")
        else:
            msgs = p.stderr.strip().splitlines() or ["unknown error"]
            err = next((m for m in msgs if m.lower().startswith(("fatal", "error"))), msgs[-1])
            print(f"Saved on this laptop, but the push failed ({err}). python tasks.py save retries.")
    except subprocess.TimeoutExpired:
        print("Saved on this laptop, but the push timed out. python tasks.py save retries.")
    except OSError as e:
        print(f"Autosave couldn't run git ({e}). Nothing was saved.")


def cmd_save(a) -> None:
    autosave(a.message or "manual save", verbose=True)


AUTOSAVE_CMDS = {"check-sql", "try-sql", "perf", "time-sql", "test", "bench", "next", "done", "status", "timer",
                 "set-interview"}


def use_venv() -> None:
    """Rerun under .venv's Python when started from another one (e.g. conda base), so nothing needs activating."""
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    in_venv = Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    if not venv.exists() or in_venv or os.environ.get("PRACTICE_IN_VENV"):
        return
    child = subprocess.Popen([str(venv), str(Path(__file__).resolve()), *sys.argv[1:]],
                             env=dict(os.environ, PRACTICE_IN_VENV="1"))
    while True:
        try:
            sys.exit(child.wait())
        except KeyboardInterrupt:
            pass  # Ctrl+C reaches the child too; wait for it to finish


def main() -> None:
    use_venv()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup-db")
    s.add_argument("--if-missing", action="store_true", help="skip if the database is already seeded")
    s.set_defaults(fn=cmd_setup_db)
    g = sub.add_parser("gen-data")
    g.add_argument("--big", type=int, help="rows for screen_rebuild/data/transactions_big.csv")
    g.add_argument("--big-mb", type=int, help="size of the data task 03 streaming file in MB")
    g.set_defaults(fn=cmd_gen_data)
    c = sub.add_parser("check-sql")
    c.add_argument("id")
    c.add_argument("--file", help="check a different .sql file")
    c.set_defaults(fn=cmd_check_sql)
    ts = sub.add_parser("try-sql")
    ts.add_argument("id")
    ts.add_argument("--reset", action="store_true", help="rewrite 02_sql/try/NN_*.txt from the problem's Example")
    ts.add_argument("--file", help="run a different .sql file")
    ts.set_defaults(fn=cmd_try_sql)
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
    n = sub.add_parser("next")
    n.add_argument("--skip-warmup", action="store_true", help="show a block even if coach reviews are due")
    n.set_defaults(fn=cmd_next)
    d = sub.add_parser("done")
    d.add_argument("id", nargs="?", help="block id; defaults to the block you're on")
    d.add_argument("--partial", metavar="WHATS_LEFT", help="tick it and queue the rest as a 10-minute block")
    d.add_argument("--undo", action="store_true", help="untick a block")
    d.set_defaults(fn=cmd_done)
    tm = sub.add_parser("timer")
    tm.add_argument("minutes", nargs="?", type=int, help="any length; default: the current block's clock")
    tm.set_defaults(fn=cmd_timer)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    bo = sub.add_parser("board")
    bo.add_argument("--no-open", action="store_true", help="only rewrite board/data.js")
    bo.set_defaults(fn=cmd_board)
    sv = sub.add_parser("save")
    sv.add_argument("message", nargs="?")
    sv.set_defaults(fn=cmd_save)
    si = sub.add_parser("set-interview")
    si.add_argument("dates", nargs="*", metavar="YYYY-MM-DD")
    si.add_argument("--clear", action="store_true", help="replace the list instead of adding to it")
    si.set_defaults(fn=cmd_set_interview)
    a = ap.parse_args()
    try:
        a.fn(a)
    finally:
        if TICKED:
            extras(report_progress)
        elif a.cmd in AUTOSAVE_CMDS:
            extras(lambda: announce_badges(progress()))  # e.g. a coach warm-up that `save` is pushing
        if a.cmd in AUTOSAVE_CMDS:
            autosave(" ".join(sys.argv[1:]) + (f" [x] {', '.join(TICKED)}" if TICKED else ""))
        extras(write_board)


if __name__ == "__main__":
    main()
