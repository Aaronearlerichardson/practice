"""Quarterly delivery SLA check for site SFTP drops.

Contract: each site's quarterly batch must land on the SFTP server by the
deadline, stated in UTC (e.g. 2026-10-15 17:00 UTC).

Arrival timestamps come from the SFTP event log as ISO-8601 strings. Most
sites' relays log with an offset ("2026-10-15T13:05:00-04:00" or "...Z");
the legacy relay logs naive strings, which are documented to be UTC.
The result rows are written to the audit table, which stores UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone


def parse_arrival(ts: str) -> datetime:
    """Parse an SFTP log timestamp."""
    return datetime.fromisoformat(ts.strip())


def check_sla(arrivals: list[dict], deadline: datetime) -> list[dict]:
    """Classify each site's arrival as on_time / late.

    arrivals: dicts with site_id and arrived_at (ISO string) or None if the
      file has not arrived yet.
    deadline: the contractual deadline (UTC).
    Returns rows: site_id, arrived_at_utc (ISO string or None), status,
      minutes_late (0 if on time, None if missing).
    """
    # Strip tzinfo so naive and aware timestamps can be compared without
    # "TypeError: can't compare offset-naive and offset-aware datetimes".
    deadline_cmp = deadline.replace(tzinfo=None)

    results = []
    for a in arrivals:
        if not a.get("arrived_at"):
            results.append({"site_id": a["site_id"], "arrived_at_utc": None,
                            "status": "missing", "minutes_late": None})
            continue
        arrived = parse_arrival(a["arrived_at"]).replace(tzinfo=None)
        late_by = (arrived - deadline_cmp).total_seconds() / 60
        results.append({
            "site_id": a["site_id"],
            "arrived_at_utc": arrived.isoformat(),
            "status": "late" if late_by > 0 else "on_time",
            "minutes_late": max(0, round(late_by)),
        })
    return results


def late_sites(results: list[dict]) -> list[str]:
    """Site IDs that are late or missing, for the escalation email."""
    return sorted(r["site_id"] for r in results if r["status"] != "on_time")


def default_deadline(year: int, quarter_due_month: int) -> datetime:
    """Deadline is 17:00 UTC on the 15th of the due month."""
    return datetime(year, quarter_due_month, 15, 17, 0, tzinfo=timezone.utc)
