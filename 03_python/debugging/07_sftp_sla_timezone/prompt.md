# 07. Site reported on time, audit log says late

**Timebox: 12 min**

## Ticket (from the site partnerships manager)

> Our Q3 SLA report says **Harbor Health (S02)** delivered on time, so no
> escalation email went out. But the SFTP audit log shows their file landed
> at 18:30 UTC, an hour and a half after the 17:00 UTC deadline. Harbor is on
> US Eastern time.
>
> Going the other way, our European partner **S05** got an escalation email
> saying they were late, and they're upset: they uploaded at 18:45 their
> time, which they say was before the deadline.
>
> The UTC-only sites and the legacy relay (naive timestamps, documented as
> UTC) look right. Also, the `arrived_at_utc` column in the audit table for
> S02 doesn't match the SFTP server's own UTC log.

Fix `buggy.py` so every arrival is compared as an absolute instant, and the
audit column really is UTC.

## Run the tests

```powershell
python -m pytest 03_python\debugging\07_sftp_sla_timezone -q
```

<details><summary>Hints</summary>

1. Print `parse_arrival("2026-10-15T14:30:00-04:00")` before and after
   `.replace(tzinfo=None)`. Which clock time survives, local or UTC?
2. `replace(tzinfo=...)` relabels a time; `astimezone(...)` converts it. Make
   every value aware first (naive means UTC here), then convert to UTC.

</details>

## Say out loud

- Reproduce: S02's arrival, deadline, and the comparison result.
- Hypothesize: the offset is discarded, so local wall-clock time is compared to UTC.
- Isolate: show the naive value is 14:30, not 18:30.
- Fix: normalize to aware UTC at the boundary (parse), compare aware to aware.
- Prevent: "aware UTC everywhere inside the pipeline" rule; reject or
  explicitly default naive input at parse time; tests with non-UTC offsets.
