from datetime import datetime, timedelta, timezone

from buggy import check_sla, default_deadline, late_sites

DEADLINE = default_deadline(2026, 10)  # 2026-10-15 17:00 UTC

ARRIVALS = [
    # Eastern site (EDT, -04:00): 14:30 local == 18:30 UTC -> 90 min late
    {"site_id": "S02", "arrived_at": "2026-10-15T14:30:00-04:00"},
    # Central European site (CEST, +02:00): 18:45 local == 16:45 UTC -> on time
    {"site_id": "S05", "arrived_at": "2026-10-15T18:45:00+02:00"},
    # Explicit UTC
    {"site_id": "S01", "arrived_at": "2026-10-15T16:59:00Z"},
    # Legacy relay: naive, documented UTC -> 2 min late
    {"site_id": "S09", "arrived_at": "2026-10-15T17:02:00"},
    # Pacific site (PDT, -07:00): 09:59 local == 16:59 UTC -> on time
    {"site_id": "S11", "arrived_at": "2026-10-15T09:59:00-07:00"},
    # not arrived
    {"site_id": "S12", "arrived_at": None},
]


def by_site(results):
    return {r["site_id"]: r for r in results}


def test_status_per_site():
    r = by_site(check_sla(ARRIVALS, DEADLINE))
    assert {k: v["status"] for k, v in r.items()} == {
        "S01": "on_time", "S02": "late", "S05": "on_time",
        "S09": "late", "S11": "on_time", "S12": "missing",
    }


def test_minutes_late():
    r = by_site(check_sla(ARRIVALS, DEADLINE))
    assert r["S02"]["minutes_late"] == 90
    assert r["S09"]["minutes_late"] == 2
    assert r["S05"]["minutes_late"] == 0
    assert r["S12"]["minutes_late"] is None


def test_audit_timestamps_are_utc():
    r = by_site(check_sla(ARRIVALS, DEADLINE))
    assert r["S02"]["arrived_at_utc"] == "2026-10-15T18:30:00+00:00"
    assert r["S05"]["arrived_at_utc"] == "2026-10-15T16:45:00+00:00"
    assert r["S09"]["arrived_at_utc"] == "2026-10-15T17:02:00+00:00"


def test_deadline_in_another_zone_means_the_same_instant():
    eastern = timezone(timedelta(hours=-4))
    same_deadline = DEADLINE.astimezone(eastern)  # 13:00-04:00
    assert check_sla(ARRIVALS, same_deadline) == check_sla(ARRIVALS, DEADLINE)


def test_escalation_list():
    assert late_sites(check_sla(ARRIVALS, DEADLINE)) == ["S02", "S09", "S12"]


def test_exactly_on_deadline_is_on_time():
    rows = check_sla([{"site_id": "S03", "arrived_at": "2026-10-15T13:00:00-04:00"}],
                     DEADLINE)
    assert rows[0]["status"] == "on_time"
    assert DEADLINE == datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)
