"""Generate and load the shared clinical practice data. Fixed seed, so every run is identical.

Normally run through `python tasks.py setup-db`, which creates the database and
applies schema.sql first. Standalone: `python 02_sql/seed.py` (uses PRACTICE_DSN).

What is planted (the problems depend on these):
- 12 sites; S10-S12 onboard late (2024-04, 2024-10, 2025-07).
- Patients: per-site fill-rate problems (NULL, '' and 'Unknown'/'U' as missing).
- Enrollments: adjacent, overlapping, contained and gapped periods; NULL end = ongoing.
- Quarterly loads: missing quarters, rejected-then-resubmitted, rejected-only.
  Labs from a quarter with no accepted load ride along in the next accepted batch.
- Labs (~1.5M rows): SI units at S04 and S09, S07 switches HGB to g/L on 2025-07-01,
  S06 writes 'mg/dl'; repeat draws at the same timestamp; late corrections
  (resent source_record_id in a later batch), double corrections, same-batch
  corrections, identical resends; implausible values (decimal slips, negatives, zeros).
"""
from __future__ import annotations

import io
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

import psycopg

SEED = 20261009
N_PATIENTS = 40_000
DATA_START = date(2023, 1, 1)
EXTRACT_END = date(2026, 6, 30)
DEFAULT_DSN = "postgresql://postgres:leet@localhost:5432/practice"

SITES = [
    # site_id, name, state, vendor, onboarded_on, patient weight
    ("S01", "Piedmont Regional Health", "NC", "Epic", date(2023, 1, 1), 12),
    ("S02", "Coastal Plain Medical Center", "NC", "Epic", date(2023, 1, 1), 10),
    ("S03", "Blue Ridge Community Hospital", "VA", "Cerner", date(2023, 1, 1), 10),
    ("S04", "Lowcountry University Health", "SC", "Epic", date(2023, 1, 1), 9),
    ("S05", "Triad Family Clinics", "NC", "Allscripts", date(2023, 1, 1), 9),
    ("S06", "Sandhills Health Partners", "NC", "Meditech", date(2023, 1, 1), 8),
    ("S07", "Tidewater Medical Group", "VA", "Cerner", date(2023, 1, 1), 9),
    ("S08", "Appalachian Valley Health", "TN", "Meditech", date(2023, 1, 1), 8),
    ("S09", "Peachtree Clinical Network", "GA", "Epic", date(2023, 1, 1), 8),
    ("S10", "Cape Fear Kidney Associates", "NC", "Epic", date(2024, 4, 1), 7),
    ("S11", "Upstate Primary Care", "SC", "Allscripts", date(2024, 10, 1), 6),
    ("S12", "Shenandoah Endocrine Group", "VA", "Cerner", date(2025, 7, 1), 4),
]
ZIP3 = {"NC": (270, 289), "SC": (290, 299), "VA": (220, 246), "TN": (370, 385), "GA": (300, 319)}

# Per-site demographic fill problems: column -> (probability missing, missing token)
FILL_DEFAULT = {"birth_date": (0.01, None), "sex": (0.005, "U"), "race": (0.08, "Unknown"),
                "ethnicity": (0.10, None), "zip3": (0.02, None)}
FILL_OVERRIDES = {
    "S03": {"race": (0.35, "Unknown"), "ethnicity": (0.40, None)},
    "S05": {"sex": (0.12, "")},
    "S08": {"birth_date": (0.25, None)},
    "S11": {"zip3": (0.45, None), "race": (0.20, None)},
    "S12": {"ethnicity": (0.60, "")},
}
RACES = ["White", "Black or African American", "Asian", "American Indian or Alaska Native",
         "Native Hawaiian or Other Pacific Islander", "Other"]
RACE_W = [60, 22, 6, 2, 1, 9]

DX = ["E11.9", "I10", "N18.3", "E78.5", "J44.9", "I50.9", "Z00.00", "R07.9", "J18.9", "N39.0",
      "K21.9", "F32.9", "M54.50", "E66.9", "I48.91", "D64.9", "R50.9", "A41.9", "E87.1", "E87.5",
      "K74.60", "R73.03", "Z79.4", "N17.9", "I21.4"]
ENC_TYPES = ["outpatient", "telehealth", "ed", "inpatient"]
ENC_W = [60, 15, 15, 10]

# test_code: (weight, canonical unit, decimals, sampler)
TESTS = {
    "GLU":   (20, "mg/dL",    0, lambda r: r.gauss(110, 30)),
    "CREAT": (15, "mg/dL",    2, lambda r: r.lognormvariate(0.0, 0.35)),
    "HGB":   (15, "g/dL",     1, lambda r: r.gauss(13.5, 1.6)),
    "K":     (15, "mmol/L",   1, lambda r: r.gauss(4.2, 0.45)),
    "NA":    (12, "mmol/L",   0, lambda r: r.gauss(139, 3)),
    "ALT":   (8,  "U/L",      0, lambda r: r.lognormvariate(3.2, 0.5)),
    "HBA1C": (7,  "%",        1, lambda r: r.gauss(6.2, 1.1)),
    "PLT":   (8,  "10*3/uL",  0, lambda r: r.gauss(250, 60)),
}
TEST_CODES = list(TESTS)
TEST_W = [TESTS[t][0] for t in TEST_CODES]
SI_SITES = {"S04", "S09"}
S07_HGB_SWITCH = datetime(2025, 7, 1)


def q_start(d: date) -> date:
    return date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)


def q_next(q: date) -> date:
    return date(q.year + (q.month == 10), 1 if q.month == 10 else q.month + 3, 1)


def q_label(q: date) -> str:
    return f"{q.year}Q{(q.month - 1) // 3 + 1}"


def ts(d: datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S")


def rand_dt(r: random.Random, d: date, h0: int, h1: int) -> datetime:
    return datetime(d.year, d.month, d.day) + timedelta(seconds=r.randrange(h0 * 3600, h1 * 3600))


def csv_field(v) -> str:
    if v is None:
        return ""
    s = str(v)
    if s == "" or any(c in s for c in ',"\n'):
        return '"' + s.replace('"', '""') + '"'  # quoted empty string stays '' (not NULL) in COPY csv
    return s


def line(*vals) -> str:
    return ",".join(csv_field(v) for v in vals) + "\n"


# ----------------------------------------------------------------------------- generators

def gen_loads(r: random.Random):
    """Returns (load rows without ids, batch_for[(site, quarter)] -> (label, received_at))."""
    loads = []
    accepted = {}  # (site, quarter) -> received_at of the accepted load
    for site_id, *_rest in SITES:
        onboard = _rest[3]
        q = q_start(onboard)
        while q <= q_start(EXTRACT_END):
            due = q_next(q)
            first = rand_dt(r, due + timedelta(days=r.randint(5, 45)), 0, 24)
            x = r.random()
            if x < 0.88:
                loads.append([site_id, q, first, "accepted"])
                accepted[(site_id, q)] = first
            elif x < 0.93:
                pass  # never delivered
            elif x < 0.97:
                loads.append([site_id, q, first, "rejected"])
                second = first + timedelta(days=r.randint(7, 21), seconds=r.randrange(86400))
                loads.append([site_id, q, second, "accepted"])
                accepted[(site_id, q)] = second
            else:
                loads.append([site_id, q, first, "rejected"])  # never fixed
            q = q_next(q)
    # Data collected in quarter q is loaded with the first accepted load at or after q.
    batch_for = {}
    for site_id, *_rest in SITES:
        onboard_q = q_start(_rest[3])
        q, pending = q_start(DATA_START), []
        while q <= q_start(EXTRACT_END):
            pending.append(q)
            if q >= onboard_q and (site_id, q) in accepted:
                for p in pending:
                    batch_for[(site_id, p)] = (f"{site_id}-{q_label(q)}", accepted[(site_id, q)])
                pending = []
            q = q_next(q)
        # quarters still pending at the end were never delivered: their labs are not in the DB
    return loads, accepted, batch_for


def later_batches(site_id: str, after: datetime, accepted: dict) -> list[tuple[str, datetime]]:
    out = [(f"{s}-{q_label(q)}", t) for (s, q), t in accepted.items() if s == site_id and t > after]
    return sorted(out, key=lambda x: x[1])


def site_unit(site_id: str, test: str, collected: datetime) -> tuple[str, float, int]:
    """(unit, multiplier from canonical, decimals) used by this site for this test."""
    canon, dec = TESTS[test][1], TESTS[test][2]
    if site_id in SI_SITES or (site_id == "S07" and test == "HGB" and collected >= S07_HGB_SWITCH):
        if test == "GLU":
            return "mmol/L", 1 / 18, 1
        if test == "CREAT":
            return "umol/L", 88.4, 0
        if test == "HGB":
            return "g/L", 10, 0
    if site_id == "S06" and canon == "mg/dL":
        return "mg/dl", 1, dec
    return canon, 1, dec


def fmt(v: float | None, dec: int) -> str | None:
    return None if v is None else f"{round(v, dec):.{dec}f}"


def main(dsn: str) -> None:
    r_load, r_pat, r_enr, r_enc, r_lab = (random.Random(SEED + i) for i in range(5))

    loads, accepted, batch_for = gen_loads(r_load)

    # ---------------- patients
    site_ids = [s[0] for s in SITES]
    site_w = [s[5] for s in SITES]
    site_state = {s[0]: s[2] for s in SITES}
    patients = []  # (patient_id, site_id)
    pat_buf = io.StringIO()
    for i in range(N_PATIENTS):
        pid = 100001 + i
        site = r_pat.choices(site_ids, site_w)[0]
        fill = {**FILL_DEFAULT, **FILL_OVERRIDES.get(site, {})}
        bd = date(1935, 1, 1) + timedelta(days=r_pat.randrange(0, 73 * 365))
        vals = {
            "birth_date": bd.isoformat(),
            "sex": r_pat.choice("FM"),
            "race": r_pat.choices(RACES, RACE_W)[0],
            "ethnicity": "Hispanic or Latino" if r_pat.random() < 0.1 else "Not Hispanic or Latino",
            "zip3": str(r_pat.randint(*ZIP3[site_state[site]])),
        }
        for col, (p, token) in fill.items():
            if r_pat.random() < p:
                vals[col] = token
        patients.append((pid, site))
        pat_buf.write(line(pid, site, vals["birth_date"], vals["sex"], vals["race"], vals["ethnicity"], vals["zip3"]))

    # ---------------- enrollments
    enr_rows = []
    span = {}  # patient -> (first_start, last_end or EXTRACT_END)
    for pid, site in patients:
        start = date(2022, 1, 1) + timedelta(days=r_enr.randrange(0, 1500))
        n = r_enr.choices([1, 2, 3, 4], [45, 30, 17, 8])[0]
        first, periods = start, []
        for _ in range(n):
            end = start + timedelta(days=r_enr.randint(60, 800))
            if end > EXTRACT_END:
                end = None
            periods.append((start, end))
            if end is None:
                break
            # occasionally a short period fully inside the current one
            if r_enr.random() < 0.06:
                cs = start + timedelta(days=r_enr.randint(1, 20))
                ce = min(cs + timedelta(days=r_enr.randint(5, 30)), end - timedelta(days=1))
                if ce > cs:
                    periods.append((cs, ce))
            x = r_enr.random()
            if x < 0.25:
                start = end + timedelta(days=1)                      # adjacent
            elif x < 0.40:
                start = end - timedelta(days=r_enr.randint(1, 30))   # overlap
            elif x < 0.50:
                start = end + timedelta(days=r_enr.randint(2, 5))    # short gap
            else:
                start = end + timedelta(days=r_enr.randint(31, 400))  # real gap
            if start > EXTRACT_END:
                break
        for s, e in periods:
            enr_rows.append((pid, site, s.isoformat(), e.isoformat() if e else None))
        span[pid] = (first, EXTRACT_END if any(e is None for _, e in periods)
                     else max(e for _, e in periods))
    r_enr.shuffle(enr_rows)
    enr_buf = io.StringIO()
    for i, row in enumerate(enr_rows, 1):
        enr_buf.write(line(i, *row))

    # ---------------- encounters
    enc_rows = []
    for pid, site in patients:
        f, l = span[pid]
        days = max((min(l, EXTRACT_END) - f).days, 1)
        for _ in range(r_enc.randint(2, 14)):
            d = f + timedelta(days=r_enc.randrange(days))
            et = r_enc.choices(ENC_TYPES, ENC_W)[0]
            if et in ("outpatient", "telehealth"):
                admit = rand_dt(r_enc, d, 8, 17)
                dis = admit + timedelta(minutes=r_enc.randint(15, 60))
            elif et == "ed":
                admit = rand_dt(r_enc, d, 0, 24)
                dis = admit + timedelta(minutes=r_enc.randint(120, 600))
            else:
                admit = rand_dt(r_enc, d, 0, 24)
                dis = admit + timedelta(days=r_enc.randint(1, 10), minutes=r_enc.randint(0, 600))
            if r_enc.random() < 0.03:
                dis = None
            dx = None if r_enc.random() < 0.05 else r_enc.choice(DX)
            prov = None if r_enc.random() < 0.02 else f"{site}-PR{r_enc.choices(range(1, 26), range(25, 0, -1))[0]:02d}"
            enc_rows.append((admit, pid, site, et, dis, dx, prov))
    enc_rows.sort(key=lambda x: (x[0], x[1]))
    enc_buf = io.StringIO()
    for i, (admit, pid, site, et, dis, dx, prov) in enumerate(enc_rows, 1):
        enc_buf.write(line(i, pid, site, et, ts(admit), ts(dis) if dis else None, dx, prov))

    # ---------------- labs
    # by_batch[(loaded_at, site)] -> list of ((record_no, version), csv tail without lab_id)
    by_batch: dict[tuple[datetime, str], list] = defaultdict(list)
    site_counter = defaultdict(int)
    batch_rows = defaultdict(int)

    def emit(loaded_at, site, key, pid, src, test, value, unit, collected, batch):
        by_batch[(loaded_at, site)].append(
            (key, line(pid, site, src, test, value, unit, ts(collected), ts(loaded_at), batch)))
        batch_rows[batch] += 1

    for pid, site in patients:
        f, l = span[pid]
        lo = max(f, DATA_START)
        hi = min(l, EXTRACT_END)
        if hi <= lo:
            lo, hi = DATA_START, date(2023, 3, 31)
        ndays = (hi - lo).days + 1
        for _ in range(r_lab.randint(15, 60)):
            collected = rand_dt(r_lab, lo + timedelta(days=r_lab.randrange(ndays)), 6, 20)
            b = batch_for.get((site, q_start(collected.date())))
            test = r_lab.choices(TEST_CODES, TEST_W)[0]
            reps = 2 if r_lab.random() < 0.01 else 1          # repeat draw, same timestamp
            for _rep in range(reps):
                canon = TESTS[test][3](r_lab)
                x = r_lab.random()
                if x < 0.0018:
                    canon *= 100                                # decimal slip
                elif x < 0.0024:
                    canon = -abs(canon)
                elif x < 0.0030:
                    canon = 0.0
                unit, mult, dec = site_unit(site, test, collected)
                value = None if r_lab.random() < 0.005 else canon * mult
                site_counter[site] += 1
                rec_no = site_counter[site]
                src = f"{site}-L{rec_no:07d}"
                if b is None:
                    continue                                    # quarter never delivered
                label, loaded_at = b
                emit(loaded_at, site, (rec_no, 0), pid, src, test, fmt(value, dec), unit, collected, label)
                y = r_lab.random()
                if y < 0.030:                                   # late correction(s)
                    later = later_batches(site, loaded_at, accepted)
                    if later:
                        n_corr = 2 if r_lab.random() < 0.12 else 1
                        picks = sorted(r_lab.sample(range(min(3, len(later))), min(n_corr, len(later), 3)))
                        base = canon if abs(canon) < 1e4 and canon > 0 else TESTS[test][3](r_lab)
                        for v, idx in enumerate(picks, 1):
                            lbl, lt = later[idx]
                            nv = base * mult * (1 + r_lab.uniform(-0.3, 0.3))
                            emit(lt, site, (rec_no, v), pid, src, test, fmt(nv, dec), unit, collected, lbl)
                elif y < 0.032:                                 # corrected inside the same batch
                    nv = (value if value is not None else canon * mult) * (1 + r_lab.uniform(-0.2, 0.2))
                    emit(loaded_at, site, (rec_no, 1), pid, src, test, fmt(nv, dec), unit, collected, label)
                elif y < 0.036:                                 # identical resend later
                    later = later_batches(site, loaded_at, accepted)
                    if later:
                        lbl, lt = later[0]
                        emit(lt, site, (rec_no, 1), pid, src, test, fmt(value, dec), unit, collected, lbl)

    # quarterly_loads ids in received order; accepted row_count = labs in that batch
    loads.sort(key=lambda x: x[2])
    load_buf = io.StringIO()
    r_cnt = random.Random(SEED + 99)
    for i, (site, q, recv, status) in enumerate(loads, 1):
        label = f"{site}-{q_label(q)}"
        n = batch_rows.get(label, 0) if status == "accepted" else r_cnt.randint(500, 9000)
        load_buf.write(line(i, site, q.isoformat(), ts(recv), status, n))

    site_buf = io.StringIO()
    for s in SITES:
        site_buf.write(line(s[0], s[1], s[2], s[3], s[4].isoformat()))

    # ---------------- load
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE labs, encounters, enrollments, quarterly_loads, patients, sites")
            for table, buf in [("sites", site_buf), ("patients", pat_buf), ("enrollments", enr_buf),
                               ("encounters", enc_buf), ("quarterly_loads", load_buf)]:
                with cur.copy(f"COPY {table} FROM STDIN (FORMAT csv)") as cp:
                    cp.write(buf.getvalue())
                print(f"  {table:<16} {buf.getvalue().count(chr(10)):>9,} rows")
            lab_id, chunk = 0, []
            with cur.copy("COPY labs FROM STDIN (FORMAT csv)") as cp:
                for key in sorted(by_batch):
                    for _, tail in sorted(by_batch[key], key=lambda x: x[0]):
                        lab_id += 1
                        chunk.append(f"{lab_id},{tail}")
                        if len(chunk) >= 50_000:
                            cp.write("".join(chunk))
                            chunk = []
                if chunk:
                    cp.write("".join(chunk))
            print(f"  {'labs':<16} {lab_id:>9,} rows")
        conn.commit()
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("VACUUM ANALYZE")


if __name__ == "__main__":
    main(os.environ.get("PRACTICE_DSN", DEFAULT_DSN) if len(sys.argv) < 2 else sys.argv[1])
