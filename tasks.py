"""Task runner for the practice repo. Works the same in PowerShell, cmd, and bash.

Every sitting:
    python tasks.py next                     the one block to do now (starts its clock)
    python tasks.py done [ID]                tick it off (defaults to the block you're on)
    python tasks.py done --partial "left"    timebox hit at ~65%: tick it, queue the rest as a small block
    python tasks.py timer                    live countdown for the current block, with a beep
    python tasks.py status                   what you've done so far
    python tasks.py save ["message"]         commit and push now (most commands already do this)
    python tasks.py set-interview 2026-10-15 [...]
                                             the day of: review only. The day before: blocks dated
                                             for that day (@YYYY-MM-DD) first, then review only

Exercises:
    python tasks.py setup-db                 create the `practice` database, schema, and ~1.5M lab rows
    python tasks.py gen-data [--big N] [--big-mb MB]
                                             regenerate the file-based exercise data
    python tasks.py check-sql 03             check 02_sql/solutions/03_*.sql against its hash
    python tasks.py perf 13                  time a performance problem before and after your fix
    python tasks.py time-sql FILE            print EXPLAIN (ANALYZE, BUFFERS) and the median runtime of one query
    python tasks.py drop-indexes             remove every non-primary-key index you created
    python tasks.py test debugging [03]      run tests (areas: screen, debugging, data, mock, all)
    python tasks.py bench 05                 run a debugging exercise's benchmark
    python tasks.py hash-sql FILE            print the hash of a query result (used to build expected/)

Database connection: set PRACTICE_DSN, e.g. in PowerShell
    $env:PRACTICE_DSN = "postgresql://postgres:leet@localhost:5432/practice"
The default below matches the local `leetpg` Docker container.

Autosave: check-sql, perf, time-sql, test, bench, next, done, status, timer and save commit everything
(your answers and coach/) and push it, so a wiped laptop never costs work again. Pushing is fail-soft.
Set PRACTICE_AUTOSAVE=0 to turn it off.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
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
STATE = ROOT / ".practice_state.json"        # gitignored: the block you're on and when its clock started
SITTING_BLOCKS = 2                           # warm-up plus this many blocks is a full sitting
BIG_FILE_MB = 20                             # autosave never commits a file bigger than this
STRANDS = {"setup": "Setup", "story": "Stories", "sql": "SQL", "debug": "Python debugging",
           "data": "Python data tasks",
           "design": "System design", "screen": "Screen rebuild", "lc": "LeetCode", "mock": "Mock"}
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
        print(f"PASS  {stem}  ({got['rows']} rows, {ms:.0f} ms)")
        tick(f"sql-{stem.split('_')[0]}", "pass")
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
        print(f"{status:<9} {f.relative_to(ROOT).as_posix():<48} {summary}")
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


@dataclass
class Block:
    id: str
    done: bool
    line: int          # index into the queue file's lines
    title: str
    body: list[str]
    anchor: date | None  # `@YYYY-MM-DD`: hidden until that day, then first in line

    @property
    def minutes(self) -> int:
        m = re.search(r"(\d+)\s*min", self.title)
        return int(m.group(1)) if m else 20

    def show(self) -> str:
        return "\n".join([f"{self.id}  {self.title}"] + [f"  {ln}" for ln in self.body])


def plain(md: str) -> str:
    return md.replace("**", "").replace("`", "").strip()


def read_queue() -> tuple[list[str], str, list[Block]]:
    raw = QUEUE.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    blocks = []
    for i, ln in enumerate(lines):
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
                            date.fromisoformat(anchor.group(1)) if anchor else None))
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


def done_today(today: date) -> int:
    return sum(e.get("date") == today.isoformat() for e in jsonl(BLOCKS_LOG))


def days_studied(today: date, days: int = 7) -> int:
    since = (today - timedelta(days=days - 1)).isoformat()
    dates = {str(e.get("date")) for e in jsonl(BLOCKS_LOG) + jsonl(COACH / "sessions.log.jsonl")}
    return sum(since <= d <= today.isoformat() for d in dates)


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
            STATE.unlink(missing_ok=True)
        COACH.mkdir(exist_ok=True)
        with BLOCKS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"date": now.date().isoformat(), "time": f"{now:%H:%M}", "block": b.id,
                                "title": b.title, "result": result, "minutes": minutes, "left": left}) + "\n")
        TICKED.append(b.id)
        print(f"[x] {b.id} done" + (f" ({minutes} min)" if minutes else "") + ".")
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
    today = date.today()
    n = done_today(today)
    before = n - len(TICKED)
    print(f"\n{n} block{'s' if n != 1 else ''} done today. You've studied {days_studied(today)} of the last 7 days.")
    if before // SITTING_BLOCKS < n // SITTING_BLOCKS:
        print("That's a full sitting. Wrap up: tell Claude \"I'm done for today\" (about 5 min with the coach).")
        print("Still in flow? python tasks.py next")
    else:
        print("Next: python tasks.py next")


def interview_near(today: date) -> date | None:
    """An interview today or tomorrow."""
    return next((d for d in interview_dates() if d - timedelta(days=1) <= today <= d), None)


def print_review_list(d: date, today: date) -> None:
    when = "today" if d == today else f"tomorrow ({d:%a %b %d})"
    print(f"Interview {when}: nothing new. This is the whole list:\n")
    print("  1. Reread your five stories (01_cross_functional/stories.md). Tell two out loud, 2 min each.")
    print("  2. Reread the red flags in 04_system_design/rubric.md and the minute budget in template.md.")
    print("  3. Reread your perf answers: the 3 sentences at the end of 02_sql/perf_lab.sql,")
    print("     and 02_sql/solutions/13_*.answer.md and 14_*.answer.md.")
    print("  4. A short warm-up with the coach is fine (\"let's study\"). Then stop for the day.")


def cmd_next(a) -> None:
    today = date.today()
    _, _, blocks = read_queue()
    todo = pending(blocks, today)
    d = interview_near(today)
    if d is not None:
        # Review only. The day before, blocks dated for that day (like the mock's gap blocks) still come first.
        todo = [b for b in todo if d != today and b.anchor == today]
        if not todo:
            print_review_list(d, today)
            return
    due = due_reviews(today)
    warmed_up = any(e.get("date") == today.isoformat() for e in jsonl(COACH / "sessions.log.jsonl"))
    if due and not warmed_up and not a.skip_warmup:
        print(f"Warm-up first: {len(due)} review{'s' if len(due) != 1 else ''} due ({', '.join(due)}).")
        print("Tell Claude \"let's study\". The ADHD study coach runs it, about 5-10 min.")
        print("Then run python tasks.py next again.  (No Claude handy? python tasks.py next --skip-warmup)")
        return
    if not todo:
        print("The queue is empty. Redo a SQL problem that felt shaky, or add blocks to 00_plan/queue.md.")
        return
    b = todo[0]
    state = load_json(STATE, {})
    now = datetime.now()
    started = datetime.fromisoformat(state["started"]) if state.get("block") == b.id else None
    if started is None or now - started > timedelta(minutes=3 * b.minutes):
        started = now
        STATE.write_text(json.dumps({"block": b.id, "started": now.isoformat(timespec="seconds"),
                                     "minutes": b.minutes}), encoding="utf-8")
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


def cmd_status(a) -> None:
    today = date.today()
    _, _, blocks = read_queue()
    counts: dict[str, int] = {}
    for b in blocks:
        if b.done:
            strand = STRANDS.get(b.id.split("-")[0], "Other")
            counts[strand] = counts.get(strand, 0) + 1
    print(f"Done so far: {sum(counts.values())} blocks")
    for strand, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {strand:<20} {'#' * n} {n}")
    n = done_today(today)
    print(f"\nToday: {n} block{'s' if n != 1 else ''}. You've studied {days_studied(today)} of the last 7 days.")
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


AUTOSAVE_CMDS = {"check-sql", "perf", "time-sql", "test", "bench", "next", "done", "status", "timer", "set-interview"}


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
            report_progress()
        if a.cmd in AUTOSAVE_CMDS:
            autosave(" ".join(sys.argv[1:]) + (f" [x] {', '.join(TICKED)}" if TICKED else ""))


if __name__ == "__main__":
    main()
