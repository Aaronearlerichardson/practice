-- 03. Quarter-over-quarter lab volume with LAG
-- Write your query below, then run: python tasks.py check-sql 03
with counts as (
    select 
        site_id,
        date_trunc('quarter', collected_at)::date as quarter_start,
        count(distinct source_record_id) as n_records
    from labs
    group by 1, 2
),
with_prev as (
    select *,
        lag(n_records) over (partition by site_id order by quarter_start) as prev_n_records
    from counts
)
select
    site_id,
    quarter_start,
    n_records,
    prev_n_records,
    round(100.0 * (n_records - prev_n_records) / prev_n_records, 2) as pct_change
from with_prev