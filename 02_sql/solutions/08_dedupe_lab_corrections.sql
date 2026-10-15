-- 08. Deduplicate corrected lab records
-- Write your query below, then run: python tasks.py check-sql 08

with s07 as (
    select *
    from labs
    where site_id = 'S07'
),
ordered as (
    select *,
    row_number() over (partition by source_record_id
    order by (loaded_at, lab_id)) as rn,
    count(*) over (partition by source_record_id) as n_versions
    from s07
),
latest as (
    select *
    from ordered
    where rn = 1
)
select
    source_record_id,
    lab_id,
    value,
    loaded_at,
    n_versions
from latest