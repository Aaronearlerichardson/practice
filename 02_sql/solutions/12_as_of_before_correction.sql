-- 12. "As of": what did we believe before the correction?
-- Write your query below, then run: python tasks.py check-sql 12

 -- Select all rows from 'labs
with s04s as (
    SELECT *
        -- source_record_id,
        -- test_code,
        -- loaded_at
    FROM labs
    -- where loaded_at > '2025-10-01 00:00:00'
    where site_id = 'S04'
),
as_of_now as (
    select *
    from ( 
        select *,
            row_number() over (partition by source_record_id order by loaded_at) as rn
        from s04s
        )
    where rn = 1
),
as_of as (
    select *
    from ( 
        select *,
            row_number() over (partition by source_record_id order by loaded_at) as rn
        from s04s
        where loaded_at < '2025-10-01 00:00:00'
        )
    where rn = 1
)
select *
from as_of_now nw;
join as_of ago on ago.source_record_id = nw.source_record_id;